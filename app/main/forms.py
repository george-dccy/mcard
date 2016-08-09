from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField, \
    IntegerField, FloatField, DateField, DateTimeField
from wtforms.validators import Length, Email, Regexp, EqualTo, DataRequired, NumberRange
from wtforms import ValidationError
from ..models import Role, User, Card, Campaign, Consume, Recharge


class NewCardForm(Form):
    cardnumber = StringField('卡号', validators=[DataRequired(), Length(1, 20, message='卡号长度错误')])
    submit = SubmitField('确定提交')

    def validate_cardnumber(self, field):
        if Card.query.filter_by(cardnumber=field.data).first():
            raise ValidationError('该卡已存在')


class RechargeForm(Form):
    cardnumber = StringField('卡号', validators=[DataRequired(), Length(1, 20, message='卡号长度错误')])
    campaign = SelectField('营销方案', coerce=int)
    channel = SelectField('付款方式', coerce=int, choices=[(1, '现金'), (2, '刷卡')])
    consumer_pay = FloatField('充值金额', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('充值')

    def __init__(self, *args, **kwargs):
        super(RechargeForm, self).__init__(*args, **kwargs)
        self.campaign.choices = [(campaign.id, campaign.description)
                                  for campaign in Campaign.query.all()]

    def validate_cardnumber(self, field):
        if Card.query.filter_by(cardnumber=field.data).first() is None:
            raise ValidationError('该卡不存在')

    def validate_campaign(self, field):
        if field.data is None:
            raise ValidationError('请联系管理员制订营销方案')


class ConsumeForm(Form):
    cardnumber = StringField('卡号', validators=[DataRequired(), Length(1, 20, message='卡号长度错误')])
    expense = FloatField('消费金额', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('提交')

    def validate_cardnumber(self, field):
        if Card.query.filter_by(cardnumber=field.data).first() is None:
            raise ValidationError('该卡不存在')

    def validate_expense(self, field):
        if Card.query.filter_by(cardnumber=field.data).first():
            if Card.query.filter_by(cardnumber=field.data).first().remaining < self.expense.data:
                raise ValidationError('余额不足')


class CardLookupForm(Form):
    cardnumber = StringField('卡号', validators=[DataRequired(), Length(1, 20, message='卡号长度错误')])
    submit = SubmitField('余额查询')

    def validate_cardnumber(self, field):
        if Card.query.filter_by(cardnumber=field.data).first() is None:
            raise ValidationError('该卡不存在')


class RecordLookupForm(Form):
    fromdate = DateField('开始日期', validators=[DataRequired()])
    todate = DateField('结束日期', validators=[DataRequired()])
