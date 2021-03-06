from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import main
from .. import db
from ..models import Permission, Role, User, Card, Campaign, Recharge, Consume
from ..decorators import admin_required, permission_required
from .forms import NewCardForm, RechargeForm, ConsumeForm, CardLookupForm, RecordLookupForm
from datetime import datetime

@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['MCARD_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response

@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', current_time=datetime.utcnow())

@main.route('/newcard', methods=['GET', 'POST'])
@login_required
def newcard():
    form = NewCardForm()
    if form.validate_on_submit():
        cardnumber = form.cardnumber.data
        card = Card(cardnumber=cardnumber,
                    owner=current_user._get_current_object())
        db.session.add(card)
        db.session.commit()
        flash('添加会员卡成功。')
        return redirect(url_for('.recharge'))
    return render_template('newcard.html', form=form)


@main.route('/recharge', methods=['GET', 'POST'])
@login_required
def recharge():
    form = RechargeForm()
    if form.validate_on_submit():
        cardnumber = form.cardnumber.data
        campaign_id = form.campaign.data
        consumer_pay = form.consumer_pay.data
        card_id = Card.query.filter_by(cardnumber=cardnumber).one().id
        changer_id = current_user._get_current_object().id
        campaign = Campaign.query.filter_by(id=campaign_id).one()
        into_card = consumer_pay + int(consumer_pay/campaign.consumer_pay)*(campaign.into_card-campaign.consumer_pay)
        newrecharge = Recharge(card_id=card_id,
                               campaign_id=campaign_id,
                               changer_id=changer_id,
                               consumer_pay=consumer_pay,
                               into_card=into_card)
        db.session.add(newrecharge)
        db.session.commit()
        flash('充值成功。')
        return redirect(url_for('main.card', card_id=card_id))
    return render_template('recharge.html', form=form)


@main.route('/consume', methods=['GET', 'POST'])
@login_required
def consume():
    form = ConsumeForm()
    if form.validate_on_submit():
        cardnumber = form.cardnumber.data
        expense = form.expense.data
        card = Card.query.filter_by(cardnumber=cardnumber).one()
        card_id = card.id
        remaining = card.remaining
        changer_id = current_user._get_current_object().id
        if expense > remaining:
            flash('余额不足。')
            return redirect(url_for('main.consume'))
        newconsume = Consume(card_id=card_id,
                             changer_id=changer_id,
                             expense=expense)
        db.session.add(newconsume)
        db.session.commit()
        flash('消费成功。')
        return redirect(url_for('main.card', card_id=card_id))
    return render_template('consume.html', form=form)

@main.route('/cardlookup', methods=['GET', 'POST'])
@login_required
def cardlookup():
    form = CardLookupForm()
    if form.validate_on_submit():
        cardnumber = form.cardnumber.data
        card = Card.query.filter_by(cardnumber=cardnumber).one()
        return redirect(url_for('main.card', card_id=card.id))
    return render_template('cardlookup.html', form=form)

@main.route('/card/<int:card_id>', methods=['GET'])
@login_required
def card(card_id):
    card = Card.query.get_or_404(card_id)
    cardnumber = card.cardnumber
    owner = card.owner.branchname
    remaining = card.remaining
    return render_template('card.html', cardnumber=cardnumber, owner=owner, remaining=remaining)