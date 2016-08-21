from flask import render_template, redirect, request, url_for, flash
from flask.ext.login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import db
from ..models import User
from .forms import LoginForm, RegUserForm
from datetime import datetime
from flask import jsonify


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.username==form.username.data).filter(User.active_flag!=-1).first()
        if user is not None:
            if user.in_use != 0 and user.verify_password(form.password.data):
                login_user(user, form.remember_me.data)
                return redirect(url_for('main.index'))
            elif user.in_use == 0:
                flash('请先激活。')
                return redirect(url_for('auth.reguser'))
        flash('用户名或密码错误。')
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


@auth.route('/reguser', methods=['POST'])
def reguser():
    form = RegUserForm()
    if form.validate_on_submit():
        username = form.username.data
        reg_code = form.reg_code.data
        reg_host = form.reg_host.data
        user = User.query.filter(User.username==username).filter(User.active_flag!=-1).first()
        if not user.is_reged() and user.reg(reg_code):
            flash('账户激活成功！')
            return redirect(url_for('auth.login'))
    form.username.data = request.args.get['username', '']
    return render_template('auth/reguser.html', form=form)