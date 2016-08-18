from app.decorators import admin_required
from flask import render_template, redirect, request, url_for, flash, send_file
from flask.ext.login import login_user, logout_user, login_required, current_user
from . import admin
from .. import db
from ..models import User, Role, Card, Campaign, Consume, Recharge
from .forms import AddUserForm, PasswordResetForm, AddCampaignForm, RecordLookupForm, AlterCampaignForm
from datetime import date, datetime, timedelta
import xlsxwriter
import io
from sqlalchemy import func

@admin.route('/adduser', methods=['GET', 'POST'])
@admin_required
def adduser():
    form = AddUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            active_flag = db.session.query(User.active_flag).filter(User.username==form.username.data).all()
            if active_flag[0][0] == -1:
                thisuser = User.query.filter_by(username=form.username.data).first()
                thisuser.active_flag = 1
                thisuser.password = form.password.data
                db.session.add(thisuser)
                db.session.commit()
                flash('成功恢复用户：'+thisuser.branchname+'，并使用新的密码登录')
                return redirect(url_for('admin.adduser'))
            else:
                flash('用户已存在')
                return redirect(url_for('admin.adduser'))
        else:
            user = User(username=form.username.data,
                        password=form.password.data,
                        branchname=form.branchname.data)
            db.session.add(user)
            db.session.commit()
            flash('添加用户：“'+form.username.data+'” 成功。')
            return redirect(url_for('admin.adduser'))
    alluser = User.query.filter(User.role_id!=2).filter(User.active_flag!=-1).order_by(User.id.desc()).all()
    return render_template('admin/adduser.html', form=form, allu=alluser)


@admin.route('/alter_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def alter_user(user_id):
    form = AddUserForm()
    thisuser = User.query.filter_by(id=user_id).one()
    if form.validate_on_submit():
        thisuser.username=form.username.data
        thisuser.branchname=form.branchname.data
        thisuser.password=form.password.data
        db.session.add(thisuser)
        db.session.commit()
        flash('成功修改用户：'+thisuser.branchname)
        return redirect(url_for('admin.adduser'))
    form.username.data=thisuser.username
    form.branchname.data=thisuser.branchname
    return render_template('admin/adduser.html', form=form, allu=None)


@admin.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def delete_user(user_id):
    thisuser = User.query.filter_by(id=user_id).one()
    username = thisuser.branchname
    thisuser.active_flag = -1
    db.session.add(thisuser)
    db.session.commit()
    flash('用户：'+username+'删除成功')
    return redirect(url_for('admin.adduser'))


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
        if Campaign.query.filter_by(description=form.description.data).first():
            active_flag = db.session.query(Campaign.active_flag).filter_by(description=form.description.data).all()
            if active_flag[0][0] == -1:
                thiscampaign = Campaign.query.filter_by(description=form.description.data).first()
                thiscampaign.active_flag = 1
                thiscampaign.consumer_pay = form.consumer_pay.data
                thiscampaign.into_card = form.into_card.data
                db.session.add(thiscampaign)
                db.session.commit()
                flash('成功恢复营销方案：'+thiscampaign.description+'，并使用新的方案。')
                return redirect(url_for('admin.add_campaign'))
            else:
                flash('该方案已存在，请重试。')
                return redirect(url_for('admin.add_campaign'))
        else:
            campaign = Campaign(description=form.description.data,
                                consumer_pay=form.consumer_pay.data,
                                into_card=form.into_card.data)
            db.session.add(campaign)
            db.session.commit()
            flash('添加营销方案：“'+form.description.data+'” 成功。')
            return redirect(url_for('admin.add_campaign'))
    campaigns = Campaign.query.filter(Campaign.active_flag!=-1).order_by(Campaign.id.desc()).all()
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
    thisCampaign.active_flag = -1
    db.session.add(thisCampaign)
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
        category = form.category.data
        user_id = form.branchname.data
        return redirect(url_for('admin.record', datefrom=datefrom, dateto=dateto, user_id=user_id, category=category))
    return render_template('admin/recordlookup.html', form=form)


@admin.route('/record', methods=['GET', 'POST'])
@admin_required
def record():
    datefrom = request.args.get('datefrom', date.today().strftime('%Y-%m-%d'), type=str)
    dateto = request.args.get('dateto', date.today().strftime('%Y-%m-%d'), type=str)
    datefrom2 = datetime.strptime(datefrom, '%Y-%m-%d') - timedelta(hours=8)
    dateto2 = datetime.strptime(dateto, '%Y-%m-%d') + timedelta(hours=16)
    user_id = request.args.get('user_id', 0, type=int)
    category = request.args.get('category', 0, type=int)
    if user_id == 0:
        branchname = "全部门店"
        if category == 1:
            category_name = "充值"
            records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname,Recharge.sn,\
                                       Recharge.consumer_pay,Recharge.channel).\
                filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).\
                filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2).all()
        else:
            category_name = "消费"
            records = db.session.query(Consume.change_time,Consume.expense,Card.cardnumber,User.branchname,Consume.sn).\
                filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).\
                filter(Consume.change_time>=datefrom2).filter(Consume.change_time<=dateto2).all()
    else:
        user = User.query.filter_by(id=user_id).one()
        branchname = user.branchname
        if category == 1:
            category_name = "充值"
            records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname,Recharge.sn,\
                                       Recharge.consumer_pay,Recharge.channel).\
                filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).filter(User.id==user_id).\
                filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2).all()
        else:
            category_name = "消费"
            records = db.session.query(Consume.change_time,Consume.expense,Card.cardnumber,User.branchname,Consume.sn).\
                filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).filter(User.id==user_id).\
                filter(Consume.change_time>=datefrom2).filter(Consume.change_time<=dateto2).all()

    return render_template('admin/record.html', records=records, datefrom=datefrom, dateto=dateto, \
                           branchname=branchname, category_name=category_name, user_id=user_id, category=category)


@admin.route('/cardreport', methods=['GET'])
@admin_required
def cardreport():
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    cards = db.session.query(Card.cardnumber.label('c'), User.branchname.label('b'), Card.remaining.label('r')).\
        filter(Card.owner_id==User.id).order_by(Card.id).all()
    total = db.session.query(func.sum(Card.remaining))

    bold = workbook.add_format({'bold': True})
    money = workbook.add_format({'num_format': '#,##0'})
    merge_format = workbook.add_format({
        'bold':     True,
        'align':    'center',
        'valign':   'vcenter',
        'font_size': 14,
    })

    worksheet.merge_range('A1:C1', '所有会员卡列表', merge_format)
    worksheet.set_row(0,height=30)
    worksheet.set_column(0,0,width=25)
    worksheet.set_column(1,1,width=15)
    worksheet.set_column(2,2,width=20)

    worksheet.write(1, 0, '卡号', bold)
    worksheet.write(1, 1, '开卡门店名', bold)
    worksheet.write(1, 2, '卡内余额(元)', bold)

    row = 2
    col = 0
    for onecard in cards:
        worksheet.write(row, col, onecard.c)
        worksheet.write(row, col+1, onecard.b)
        worksheet.write(row, col+2, onecard.r, money)
        row += 1
    worksheet.write(row+1, col, '余额总计', bold)
    worksheet.write(row+1, col+2, total[0][0], money)
    workbook.close()
    output.seek(0)
    filename = 'cardReport' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xlsx'
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",\
                     as_attachment=True, attachment_filename=filename)


@admin.route('/printrecord', methods=['GET'])
@admin_required
def printrecord():
    datefrom = request.args.get('datefrom', date.today().strftime('%Y-%m-%d'), type=str)
    dateto = request.args.get('dateto', date.today().strftime('%Y-%m-%d'), type=str)
    datefrom2 = datetime.strptime(datefrom, '%Y-%m-%d') - timedelta(hours=8)
    dateto2 = datetime.strptime(dateto, '%Y-%m-%d') + timedelta(hours=16)
    category = request.args.get('category', 0, type=int)
    user_id = request.args.get('user_id', 0, type=int)

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()
    worksheet.set_row(0, height=30)
    worksheet.set_column(0, 0, width=25)
    worksheet.set_column(1, 1, width=15)
    bold = workbook.add_format({'bold': True})
    money = workbook.add_format({'num_format': '#,##0'})
    merge_format = workbook.add_format({
        'bold':     True,
        'align':    'center',
        'valign':   'vcenter',
        'font_size': 14,
    })

    if category == 1:
        category_name = "充值"
        if user_id == 0:
            branchname = "全部门店"
            records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname,Recharge.sn,\
                                       Recharge.consumer_pay,Recharge.channel).\
                filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).\
                filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2).all()
            total = db.session.query(func.sum(Recharge.consumer_pay)).\
                filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).\
                filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2)
        else:
            user = User.query.filter_by(id=user_id).one()
            branchname = user.branchname
            records = db.session.query(Recharge.into_card,Recharge.change_time,Card.cardnumber,User.branchname,Recharge.sn,\
                                       Recharge.consumer_pay,Recharge.channel).\
                filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).filter(User.id==user_id).\
                filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2).all()
            total = db.session.query(func.sum(Recharge.consumer_pay)).\
                filter(Recharge.card_id==Card.id).filter(Recharge.changer_id==User.id).filter(User.id==user_id).\
                filter(Recharge.change_time>=datefrom2).filter(Recharge.change_time<=dateto2)

        worksheet.set_column(5, 5, width=15)
        worksheet.set_column(6, 6, width=20)

        worksheet.merge_range('A1:G1', datefrom+' 00:00:00 到'+dateto+' 24:00:00 在'+branchname+'的'+category_name+'记录', merge_format)
        worksheet.write(1, 0, '流水号', bold)
        worksheet.write(1, 1, '卡号', bold)
        worksheet.write(1, 2, '支付方式', bold)
        worksheet.write(1, 3, '支付金额', bold)
        worksheet.write(1, 4, '入卡金额', bold)
        worksheet.write(1, 5, '门店', bold)
        worksheet.write(1, 6, '充值时间', bold)

        row = 2
        col = 0
        for onerecord in records:
            worksheet.write(row, col, onerecord.sn)
            worksheet.write(row, col+1, onerecord.cardnumber)
            if onerecord.channel == 1:
                worksheet.write(row, col+2, "现金")
            else:
                worksheet.write(row, col+2, "刷卡")
            worksheet.write(row, col+3, onerecord.consumer_pay, money)
            worksheet.write(row, col+4, onerecord.into_card, money)
            worksheet.write(row, col+5, onerecord.branchname)
            worksheet.write(row, col+6, (onerecord.change_time+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'))
            row += 1
        worksheet.write(row+1, col, '充值总计', bold)
        worksheet.write(row+1, col+3, total[0][0], money)
        workbook.close()
        output.seek(0)
        filename = 'rechargeRecord' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xlsx'
        return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",\
                         as_attachment=True, attachment_filename=filename)
    else:
        category_name = "消费"
        if user_id == 0:
            branchname = "全部门店"
            records = db.session.query(Consume.change_time,Consume.expense,Card.cardnumber,User.branchname,Consume.sn).\
                filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).\
                filter(Consume.change_time>=datefrom2).filter(Consume.change_time<=dateto2).all()
            total = db.session.query(func.sum(Consume.expense)).\
                filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).\
                filter(Consume.change_time>=datefrom2).filter(Consume.change_time<=dateto2)
        else:
            user = User.query.filter_by(id=user_id).one()
            branchname = user.branchname
            records = db.session.query(Consume.change_time,Consume.expense,Card.cardnumber,User.branchname,Consume.sn).\
                filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).filter(User.id==user_id).\
                filter(Consume.change_time>=datefrom2).filter(Consume.change_time<=dateto2).all()
            total = db.session.query(func.sum(Consume.expense)).\
                filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).filter(User.id==user_id).\
                filter(Consume.change_time>=datefrom2).filter(Consume.change_time<=dateto2)

        worksheet.set_column(3, 3, width=15)
        worksheet.set_column(4, 4, width=20)

        worksheet.merge_range('A1:E1', datefrom+' 00:00:00 到'+dateto+' 24:00:00 在'+branchname+'的'+category_name+'记录', merge_format)

        worksheet.write(1, 0, '流水号', bold)
        worksheet.write(1, 1, '卡号', bold)
        worksheet.write(1, 2, '消费金额', bold)
        worksheet.write(1, 3, '门店', bold)
        worksheet.write(1, 4, '消费时间', bold)

        row = 2
        col = 0
        for onerecord in records:
            worksheet.write(row, col, onerecord.sn)
            worksheet.write(row, col+1, onerecord.cardnumber)
            worksheet.write(row, col+2, onerecord.expense, money)
            worksheet.write(row, col+3, onerecord.branchname)
            worksheet.write(row, col+4, (onerecord.change_time+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'))
            row += 1
        worksheet.write(row+1, col, '消费总计', bold)
        worksheet.write(row+1, col+2, total[0][0], money)
        workbook.close()
        output.seek(0)
        filename = 'rechargeRecord' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xlsx'
        return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",\
                         as_attachment=True, attachment_filename=filename)
