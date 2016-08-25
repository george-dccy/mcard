from app.decorators import admin_required
from flask import render_template, redirect, request, url_for, flash, send_file
from flask.ext.login import login_user, logout_user, login_required, current_user
from . import admin
from .. import db
from ..models import User, Role, Card, Campaign, Consume, Recharge
from .forms import AddUserForm, PasswordResetForm, AddCampaignForm, RecordLookupForm, AlterCampaignForm, CardInitForm
from ..main.forms import CardLookupForm
from datetime import date, datetime, timedelta
import xlsxwriter
import io
from sqlalchemy import func
import shortuuid
from ..email import send_email

##'''用户管理'''
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
            reg_code = shortuuid.uuid()[0:10]
            user = User(username=form.username.data,
                        password=form.password.data,
                        branchname=form.branchname.data,
                        reg_code=reg_code)
            db.session.add(user)
            db.session.commit()
            send_email('dccy99@qq.com', '新用户申请', 'auth/email/userapply', \
                       username=form.username.data, password=form.password.data, reg_code=reg_code)
            flash('申请用户：“'+form.username.data+'” 成功。请联系我们索取验证码。')
            return redirect(url_for('admin.adduser'))
    alluser = User.query.filter(User.role_id!=2).filter(User.active_flag!=-1).order_by(User.id.desc()).all()
    return render_template('admin/adduser.html', form=form, allu=alluser)


@admin.route('/alter_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def alter_user(user_id):
    form = AddUserForm()
    thisuser = User.query.filter(User.id==user_id).filter(User.active_flag!=-1).filter(User.in_use!=0).one()
    form.username.data=thisuser.username
    form.branchname.data=thisuser.branchname
    if form.validate_on_submit():
        if thisuser:
            if not thisuser.is_administrator:
                thisuser.username=form.username.data
                thisuser.branchname=form.branchname.data
                thisuser.password=form.password.data
                db.session.add(thisuser)
                db.session.commit()
                flash('成功修改用户：'+thisuser.branchname)
                return redirect(url_for('admin.adduser'))
            else:
                flash('修改失败，请重试')
                return redirect(url_for('admin.alter_user', user_id=user_id))
        else:
            flash('用户不允许修改')
            return redirect((url_for('main.index')))
    return render_template('admin/adduser.html', form=form, allu=None)


@admin.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def delete_user(user_id):
    thisuser = User.query.filter_by(id=user_id).one()
    if thisuser.is_administrator():
        flash('不可删除管理员用户。')
        return redirect(url_for('admin.adduser'))
    username = thisuser.branchname
    thisuser.active_flag = -1
    db.session.add(thisuser)
    db.session.commit()
    flash('用户：'+username+'删除成功')
    return redirect(url_for('admin.adduser'))


@admin.route('/delete_user_complete/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def delete_user_complete(user_id):
    thisuser = User.query.filter_by(id=user_id).one()
    if thisuser.is_administrator() or thisuser.in_use:
        flash('不可完全删除管理员用户或已激活用户。')
        return redirect(url_for('admin.adduser'))
    username = thisuser.branchname
    db.session.delete(thisuser)
    db.session.commit()
    flash('用户：'+username+'已完全删除。')
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

##'''营销方案管理'''
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
                if form.validate_last_for.data:
                    thiscampaign.validate_last_for = form.validate_last_for.data
                else:
                    thiscampaign.validate_last_for = 360
                db.session.add(thiscampaign)
                db.session.commit()
                flash('成功恢复营销方案：'+thiscampaign.description+'，并使用新的方案。')
                return redirect(url_for('admin.add_campaign'))
            else:
                flash('该方案已存在，请重试。')
                return redirect(url_for('admin.add_campaign'))
        else:
            if form.validate_last_for.data:
                validate_last_for = form.validate_last_for.data
            else:
                validate_last_for = 360
            campaign = Campaign(description=form.description.data,
                                consumer_pay=form.consumer_pay.data,
                                into_card=form.into_card.data,
                                validate_last_for=validate_last_for)
            db.session.add(campaign)
            db.session.commit()
            flash('添加营销方案：“'+form.description.data+'” 成功。')
            return redirect(url_for('admin.add_campaign'))
    campaigns = Campaign.query.filter(Campaign.active_flag!=-1).order_by(Campaign.priority.desc()).order_by(Campaign.id.desc()).all()
    count = Campaign.query.filter(Campaign.active_flag!=-1).count()
    return render_template('admin/campaign.html', form=form, campaigns=campaigns, count=count)


@admin.route('/alter_campaign/<int:campaign_id>', methods=['GET', 'POST'])
@admin_required
def alter_campaign(campaign_id):
    form = AlterCampaignForm()
    thisCampaign = Campaign.query.filter_by(id=campaign_id).one()
    if form.validate_on_submit():
        if thisCampaign.active_flag == -1:
            flash('已删除方案，不可更改！')
            return redirect(url_for('admin.add_campaign'))
        else:
            thisCampaign.description = form.description.data
            thisCampaign.consumer_pay = form.consumer_pay.data
            thisCampaign.into_card = form.into_card.data
            thisCampaign.validate_last_for = form.validate_last_for.data
            db.session.add(thisCampaign)
            db.session.commit()
            flash('修改营销方案：“'+thisCampaign.description+'” 成功。')
            return redirect(url_for('admin.add_campaign'))
    form.description.data = thisCampaign.description
    form.consumer_pay.data = thisCampaign.consumer_pay
    form.into_card.data = thisCampaign.into_card
    form.validate_last_for = thisCampaign.validate_last_for
    return render_template('admin/campaign.html', form=form, campaigns=None)


@admin.route('/setdefaultcampaign/<int:campaign_id>', methods=['GET'])
@admin_required
def setdefaultcampaign(campaign_id):
    thisCampaign = Campaign.query.filter_by(id=campaign_id).filter(Campaign.active_flag!=-1).one()
    if thisCampaign:
        Campaign.query.update({'priority': 0})
        db.session.commit()
        thisCampaign.priority = 9
        db.session.add(thisCampaign)
        db.session.commit()
        flash('方案：'+thisCampaign.description+'已设置为默认。')
        return redirect(url_for('admin.add_campaign'))
    else:
        flash('未设置成功，请重试。')
        return redirect(url_for('admin.add_campaign'))


@admin.route('/delete_campaign/<int:campaign_id>', methods=['GET'])
@admin_required
def delete_campaign(campaign_id):
    if Campaign.query.filter(Campaign.active_flag!=-1).count() <= 1:
        flash('最后一个方案，不允许删除。')
        return redirect(url_for('admin.add_campaign'))
    thisCampaign = Campaign.query.filter_by(id=campaign_id).one()
    thisCampaign.active_flag = -1
    db.session.add(thisCampaign)
    db.session.commit()
    flash('删除营销方案： “'+thisCampaign.description+'” 成功。')
    return redirect(url_for('admin.add_campaign'))


##'''卡管理'''
@admin.route('/cardinit', methods=['GET', 'POST'])
@admin_required
def cardinit():
    form = CardInitForm()
    if form.validate_on_submit():
        cardnumber = form.cardnumber.data
        thiscard = Card.query.filter_by(cardnumber=cardnumber).first()
        if thiscard:
            flash('卡号为'+cardnumber+'的卡已存在，请进入卡管理-->卡查询。')
            return redirect(url_for('admin.cardinit'))
        else:
            campaign_id = form.campaign.data
            thiscampaign = Campaign.query.filter_by(id=campaign_id).first()
            into_card = thiscampaign.into_card
            validate_last_for = thiscampaign.validate_last_for
            validate_consumer_pay = thiscampaign.consumer_pay
            validate_into_card = thiscampaign.into_card
            card = Card(cardnumber=cardnumber,
                        remaining=into_card,
                        validate_start_time=datetime.utcnow(),
                        validate_last_for=validate_last_for,
                        validate_consumer_pay=validate_consumer_pay,
                        validate_into_card=validate_into_card,
                        owner=current_user._get_current_object())
            db.session.add(card)
            db.session.commit()
            flash('添加'+cardnumber+'成功。')
            return redirect(url_for('admin.cardinit'))
    return render_template('admin/cardinit.html', form=form)


@admin.route('/cardlookup', methods=['GET', 'POST'])
@admin_required
def cardlookup():
    form = CardLookupForm()
    if form.validate_on_submit():
        cardnumber = form.cardnumber.data
        card = Card.query.filter_by(cardnumber=cardnumber).one()
        return redirect(url_for('admin.card', card_id=card.id))
    return render_template('admin/cardlookup.html', form=form)


@admin.route('/card/<int:card_id>', methods=['GET', 'POST'])
@admin_required
def card(card_id):
    thiscard = Card.query.filter_by(id=card_id).first()
    if thiscard:
        owner = thiscard.owner.branchname

        lastconsume = db.session.query(Consume.sn,Card.cardnumber,Consume.expense,User.branchname,Consume.change_time).\
            filter(Card.id==thiscard.id).filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).\
            order_by(Consume.change_time.desc()).limit(2).all()
        #return render_template('admin/cardlookup.html', cardnumber=cardnumber, owner=owner, remaining=remaining,)
        return render_template('admin/card.html', thiscard=thiscard, owner=owner, lastconsume=lastconsume)
    else:
        flash('没有会员卡信息。')
        return redirect(url_for('admin.cardlookup'))

@admin.route('/alter_card', methods=['GET', 'POST'])
@admin_required
def alter_card():
    pass


@admin.route('/delect_card/<int:card_id>', methods=['GET', 'POST'])
@admin_required
def delect_card(card_id):
    thiscard = Card.query.filter_by(id=card_id).first()
    if thiscard:
        db.session.delete(thiscard)
        db.session.commit()
        flash('会员卡注销成功。')
        return redirect(url_for('admin.cardinit'))


##'''充值和消费记录管理'''
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
            category_name = "激活"
            records = db.session.query(Card.validate_into_card,Card.validate_start_time,Card.cardnumber,User.branchname,Card.validate_sn,\
                                       Card.validate_consumer_pay,Card.validate_channel)\
                .filter(Card.owner_id==User.id).filter(Card.validate_start_time>=datefrom2).filter(Card.validate_start_time<=dateto2).all()
        else:
            category_name = "消费"
            records = db.session.query(Consume.change_time,Consume.expense,Card.cardnumber,User.branchname,Consume.sn).\
                filter(Consume.card_id==Card.id).filter(Consume.changer_id==User.id).\
                filter(Consume.change_time>=datefrom2).filter(Consume.change_time<=dateto2).all()
    else:
        user = User.query.filter_by(id=user_id).one()
        branchname = user.branchname
        if category == 1:
            category_name = "激活"
            records = db.session.query(Card.validate_into_card,Card.validate_start_time,Card.cardnumber,User.branchname,Card.validate_sn,\
                                       Card.validate_consumer_pay,Card.validate_channel).filter(User.id==user_id)\
                .filter(Card.owner_id==User.id).filter(Card.validate_start_time>=datefrom2).filter(Card.validate_start_time<=dateto2).all()
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

    cards = db.session.query(Card.cardnumber, User.branchname, Card.remaining, Card.in_use, Card.validate_start_time, \
                             Card.validate_channel, Card.validate_until, Card.validate_consumer_pay).\
        filter(Card.owner_id==User.id).order_by(Card.id).all()
    total = db.session.query(func.sum(Card.remaining))
    total_consumer_pay = db.session.query(func.sum(Card.validate_consumer_pay)).filter(Card.in_use==1)

    bold = workbook.add_format({'bold': True})
    money = workbook.add_format({'num_format': '#,##0.00'})
    merge_format = workbook.add_format({
        'bold':     True,
        'align':    'center',
        'valign':   'vcenter',
        'font_size': 14,
    })

    worksheet.merge_range('A1:H1', '所有会员卡列表', merge_format)
    worksheet.set_row(0,height=30)
    worksheet.set_column(0,0,width=25)
    worksheet.set_column(1,1,width=15)
    worksheet.set_column(2,2,width=15)
    worksheet.set_column(3,3,width=10)
    worksheet.set_column(4,4,width=21)
    worksheet.set_column(5,5,width=10)
    worksheet.set_column(6,6,width=15)
    worksheet.set_column(7,7,width=16)

    worksheet.write(1, 0, '卡号', bold)
    worksheet.write(1, 1, '开卡门店名', bold)
    worksheet.write(1, 2, '卡内余额(元)', bold)
    worksheet.write(1, 3, '状态', bold)
    worksheet.write(1, 4, '激活时间', bold)
    worksheet.write(1, 5, '激活方式', bold)
    worksheet.write(1, 6, '付款金额', bold)
    worksheet.write(1, 7, '有效期至', bold)

    row = 2
    col = 0
    for onecard in cards:
        worksheet.write(row, col, onecard.cardnumber)
        worksheet.write(row, col+1, onecard.branchname)
        worksheet.write(row, col+2, onecard.remaining, money)
        if onecard.in_use == 1:
            if datetime.now().date() > onecard.validate_until.date():
                worksheet.write(row, col+3, '已过期')
            else:
                worksheet.write(row, col+3, '已激活')
            if onecard.validate_channel == 1:
                worksheet.write(row, col+5, '现金')
            else:
                worksheet.write(row, col+5, '刷卡')
            worksheet.write(row, col+4, (onecard.validate_start_time+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'))
            worksheet.write(row, col+6, onecard.validate_consumer_pay, money)
            worksheet.write(row, col+7, (onecard.validate_until+timedelta(hours=8)).strftime('%Y-%m-%d'))
        else:
            worksheet.write(row, col+3, '未激活')

        row += 1
    worksheet.write(row+1, col, '总计', bold)
    worksheet.write(row+1, col+2, total[0][0], money)
    worksheet.write(row+1, col+6, total_consumer_pay[0][0], money)
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
    money = workbook.add_format({'num_format': '#,##0.00'})
    merge_format = workbook.add_format({
        'bold':     True,
        'align':    'center',
        'valign':   'vcenter',
        'font_size': 14,
    })

    if category == 1:
        category_name = "激活"
        if user_id == 0:
            branchname = "全部门店"
            records = db.session.query(Card.validate_into_card,Card.validate_start_time,Card.cardnumber,User.branchname,Card.validate_sn,\
                                       Card.validate_consumer_pay,Card.validate_channel).filter(Card.owner_id==User.id).\
                filter(Card.in_use==1).filter(Card.validate_start_time>=datefrom2).filter(Card.validate_start_time<=dateto2).all()
            total = db.session.query(func.sum(Card.validate_consumer_pay)).filter(Card.in_use==1).\
                filter(Card.validate_start_time>=datefrom2).filter(Card.validate_start_time<=dateto2)
        else:
            user = User.query.filter_by(id=user_id).one()
            branchname = user.branchname
            records = db.session.query(Card.validate_into_card,Card.validate_start_time,Card.cardnumber,User.branchname,Card.validate_sn,\
                                       Card.validate_consumer_pay,Card.validate_channel).filter(Card.owner_id==User.id).filter(User.id==user_id).\
                filter(Card.in_use==1).filter(Card.validate_start_time>=datefrom2).filter(Card.validate_start_time<=dateto2).all()
            total = db.session.query(func.sum(Card.validate_consumer_pay)).filter(Card.in_use==1).filter(User.id==user_id).\
                filter(Card.validate_start_time>=datefrom2).filter(Card.validate_start_time<=dateto2)

        worksheet.set_column(5, 5, width=15)
        worksheet.set_column(6, 6, width=20)

        worksheet.merge_range('A1:G1', datefrom+' 00:00:00 到'+dateto+' 24:00:00 在'+branchname+'的'+category_name+'记录', merge_format)
        worksheet.write(1, 0, '流水号', bold)
        worksheet.write(1, 1, '卡号', bold)
        worksheet.write(1, 2, '支付方式', bold)
        worksheet.write(1, 3, '支付金额', bold)
        worksheet.write(1, 4, '入卡金额', bold)
        worksheet.write(1, 5, '门店', bold)
        worksheet.write(1, 6, '激活时间', bold)

        row = 2
        col = 0
        for onerecord in records:
            worksheet.write(row, col, onerecord.validate_sn)
            worksheet.write(row, col+1, onerecord.cardnumber)
            if onerecord.validate_channel == 1:
                worksheet.write(row, col+2, "现金")
            else:
                worksheet.write(row, col+2, "刷卡")
            worksheet.write(row, col+3, onerecord.validate_consumer_pay, money)
            worksheet.write(row, col+4, onerecord.validate_into_card, money)
            worksheet.write(row, col+5, onerecord.branchname)
            worksheet.write(row, col+6, (onerecord.validate_start_time+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'))
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
