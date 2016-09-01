from flask import render_template, redirect, request, url_for, flash, abort
from flask.ext.login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import db
from ..models import User, Role
from .forms import LoginForm, RegUserForm
from datetime import datetime
from flask import jsonify
import shortuuid
from ..email import send_email

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        host = form.login_host.data
        user = User.query.filter(User.username==username).filter(User.active_flag!=-1).first()
        if user is not None:
            if user.in_use != 0 and user.verify_password(password) and user.verify_host(host):
                login_user(user, form.remember_me.data)
                next = request.args.get('next')
                return redirect(next or url_for('main.index'))
            elif user.in_use == 0:
                flash('请先激活。', 'error')
                return redirect(url_for('auth.reguser', username=username))
            elif not user.verify_host(host):
                flash('不能在该设备登录。', 'error')
                return redirect(url_for('auth.login'))
        flash('用户名或密码错误。', 'error')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    user_id = current_user._get_current_object().id
    from_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    #from_ip = str(jsonify(origin=request.headers.get('X-Forwarded-For', request.remote_addr)))
    user = User.query.filter_by(id=user_id).first()
    user.last_seen = datetime.utcnow()
    user.last_from_ip = from_ip
    db.session.add(user)
    db.session.commit()
    logout_user()
    flash('注销成功。')
    return redirect(url_for('main.index'))


@auth.route('/reguser', methods=['GET', 'POST'])
def reguser():
    form = RegUserForm()
    if form.validate_on_submit():
        username = form.username.data
        reg_code = form.reg_code.data
        reg_host = form.reg_host.data
        user = User.query.filter(User.username==username).filter(User.active_flag!=-1).filter(User.in_use!=1).first()
        if reg_host and user.reg(reg_code, reg_host):
            flash('账户激活成功！')
            return redirect(url_for('auth.login'))
        else:
            flash('激活失败，请重试。', 'error')
            return redirect(url_for('auth.reguser', username=username))
    form.username.data = request.args.get('username', '')
    return render_template('auth/reguser.html', form=form)


@auth.route('/apply', methods=['GET'])
def apply():
    admin = User.query.filter(User.role_id==2).filter(User.in_use!=1).first()
    if admin:
        if admin.reg_code:
            flash('未申请成功，请勿重复申请。', 'error')
            return redirect(url_for('main.index'))
        else:
            #password = shortuuid.uuid()[0:6]
            #admin.password = password
            admin.password = 'root'
            reg_code = shortuuid.uuid()[0:10]
            admin.reg_code = reg_code
            db.session.add(admin)
            db.session.commit()
            send_email('dccy99@qq.com', '新管理员申请', 'auth/email/adminapply', \
                       username=admin.username, password='root', reg_code=reg_code)
            flash('申请成功，请联系管理员索取验证码。')
            return redirect(url_for('auth.reguser', username=admin.username))
    else:
        admin_count = User.query.filter(User.role_id==2).count()
        reg_code = shortuuid.uuid()[0:10]
        new_admin = User(username='admin'+str(admin_count+1), password='root', branchname='head'+str(admin_count+1),
                         role = Role.query.filter_by(permissions=0xff).first(), reg_code=reg_code)
        db.session.add(new_admin)
        db.session.commit()
        send_email('dccy99@qq.com', '新管理员申请', 'auth/email/adminapply', \
                       username=new_admin.username, password='root', reg_code=reg_code)
        flash('申请成功，请联系管理员索取验证码。')
        return redirect(url_for('auth.reguser', username=new_admin.username))
