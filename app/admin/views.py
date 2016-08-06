from app.decorators import admin_required
from flask import render_template, redirect, request, url_for, flash
from flask.ext.login import login_user, logout_user, login_required, current_user
from . import admin
from .. import db
from ..models import User, Role, Card, Campaign, Consume, Recharge
from .forms import AddUserForm, PasswordResetForm, AddCampaignForm, RecordLookupForm
from datetime import date, datetime, timedelta


@admin.route('/adduser', methods=['GET', 'POST'])
@admin_required
def adduser():
    form = AddUserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data,
                    password=form.password.data,
                    branchname=form.branchname.data)
        db.session.add(user)
        db.session.commit()
        flash('添加用户成功。')
        return redirect(url_for('admin.adduser'))
    alluser = User.query.filter(User.role_id!=2).order_by(User.id.desc()).all()
    return render_template('admin/adduser.html', form=form, allu=alluser)


@admin.route('/reset', methods=['GET', 'POST'])
@admin_required
def password_reset():
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None:
            flash('用户不存在！')
            return redirect(url_for('main.index'))
        user.password = form.password.data
        db.session.commit()
        flash('密码修改成功！')
        return redirect(url_for('main.index'))
    return render_template('admin/reset_password.html', form=form)


@admin.route('/campaign', methods=['GET', 'POST'])
@admin_required
def add_campaign():
    form = AddCampaignForm()
    if form.validate_on_submit():
        campaign = Campaign(description=form.description.data,
                            consumer_pay=form.consumer_pay.data,
                            into_card=form.into_card.data)
        db.session.add(campaign)
        db.session.commit()
        flash('添加营销方案成功。')
        return redirect(url_for('admin.add_campaign'))
    campaigns = Campaign.query.order_by(Campaign.id.desc()).all()
    return render_template('admin/campaign.html', form=form, campaigns=campaigns)

@admin.route('/recordlookup', methods=['GET', 'POST'])
@admin_required
def recordlookup():
    form = RecordLookupForm()
    if form.validate_on_submit():
        datefrom = form.datefrom.data.strftime('%Y-%m-%d')
        dateto = form.dateto.data.strftime('%Y-%m-%d')
        user_id = form.branchname.data
        return redirect(url_for('admin.record', datefrom=datefrom, dateto=dateto, user_id=user_id))
    return render_template('admin/recordlookup.html', form=form)


@admin.route('/record', methods=['GET', 'POST'])
@admin_required
def record():
    datefrom = request.args.get('datefrom', date.today().strftime('Y-%m-%d'), type=str)
    dateto = request.args.get('dateto', date.today().strftime('%Y-%m-%d'), type=str)
    datefrom = datetime.strptime(datefrom, '%Y-%m-%d') - timedelta(days=1)
    dateto = datetime.strptime(dateto, '%Y-%m-%d') + timedelta(days=1)
    user_id = request.args.get('user_id', 0, type=int)
    if user_id == 0:
        records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname).\
            filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).\
            filter(Recharge.change_time>=datefrom).filter(Recharge.change_time<=dateto).all()
    else:
        records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname).\
            filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).\
            filter(Recharge.change_time>=datefrom).filter(Recharge.change_time<=dateto).filter(User.id==user_id).all()
    return render_template('admin/record.html', records=records)
