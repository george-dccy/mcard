from app.decorators import admin_required
from flask import render_template, redirect, request, url_for, flash
from flask.ext.login import login_user, logout_user, login_required, current_user
from . import admin
from .. import db
from ..models import User, Role, Card, Campaign, Consume, Recharge
from .forms import AddUserForm, PasswordResetForm, AddCampaignForm, RecordLookupForm, AlterCampaignForm
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
        flash('添加用户：“'+form.username.data+'” 成功。')
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
        flash(user.username+'的密码修改成功！')
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
        flash('添加营销方案：“'+form.description.data+'” 成功。')
        return redirect(url_for('admin.add_campaign'))
    campaigns = Campaign.query.order_by(Campaign.id.desc()).all()
    return render_template('admin/campaign.html', form=form, campaigns=campaigns)


@admin.route('/alter_campaign/<int:campaign_id>', methods=['GET', 'POST'])
@admin_required
def alter_campaign(campaign_id):
    form = AlterCampaignForm()
    thisCampaign = Campaign.query.filter_by(id=campaign_id).one()
    if form.validate_on_submit():
        thisCampaign.description = form.description.data
        thisCampaign.consumer_pay = form.consumer_pay.data
        thisCampaign.into_card = form.into_card.data
        db.session.add(thisCampaign)
        db.session.commit()
        flash('修改营销方案：“'+thisCampaign.description+'” 成功。')
        return redirect(url_for('admin.add_campaign'))
    form.description.data = thisCampaign.description
    form.consumer_pay.data = thisCampaign.consumer_pay
    form.into_card.data = thisCampaign.into_card
    return render_template('admin/campaign.html', form=form, campaigns=None)

@admin.route('/delete_campaign/<int:campaign_id>', methods=['GET'])
@admin_required
def delete_campaign(campaign_id):
    thisCampaign = Campaign.query.filter_by(id=campaign_id).one()
    db.session.delete(thisCampaign)
    db.session.commit()
    flash('删除营销方案： “'+thisCampaign.description+'” 成功。')
    return redirect(url_for('admin.add_campaign'))


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
    datefrom2 = datetime.strptime(datefrom, '%Y-%m-%d') - timedelta(hours=12)
    dateto2 = datetime.strptime(dateto, '%Y-%m-%d') + timedelta(hours=12)
    user_id = request.args.get('user_id', 0, type=int)
    if user_id == 0:
        branchname = "全部门店"
        records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname,Recharge.sn,\
                                   Recharge.consumer_pay,Recharge.channel).\
            filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).\
            filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2).all()
    else:
        user = User.query.filter_by(id=user_id).one()
        branchname = user.branchname
        records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname,Recharge.sn,\
                                   Recharge.consumer_pay,Recharge.channel).\
            filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).\
            filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2).filter(User.id==user_id).all()
    return render_template('admin/record.html', records=records, datefrom=datefrom, dateto=dateto, branchname=branchname)
