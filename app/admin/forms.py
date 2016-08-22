from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, SubmitField, FloatField, IntegerField, DateField, SelectField
from wtforms.validators import Length, Email, Regexp, EqualTo, DataRequired, NumberRange
from wtforms import ValidationError
from ..models import User

class AddUserForm(Form):
    username = StringField('用户名', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.-]*$', 0,
                                          '用户名只包含数字、字母、点号、横线和下划线 ')])
    password = PasswordField('密码', validators=[DataRequired(), EqualTo('password2', message='密码不匹配')])
    password2 = PasswordField('确认密码', validators=[DataRequired()])
    branchname = StringField('分店名', validators=[DataRequired()])
    submit = SubmitField('确认')


class PasswordResetForm(Form):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('新密码', validators=[
        DataRequired(), EqualTo('password2', message='密码不一致')])
    password2 = PasswordField('确认密码', validators=[DataRequired()])
    submit = SubmitField('修改密码')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first() is None:
            raise ValidationError('用户不存在')


class AddCampaignForm(Form):
    description = StringField('方案名称', validators=[DataRequired()])
    consumer_pay = FloatField('付款金额', validators=[DataRequired(),
                                                  NumberRange(min=0, max=None, message='充值金额不能小于0')])
    into_card = FloatField('入卡金额', validators=[DataRequired(),
                                                  NumberRange(min=0, max=None, message='充值金额不能小于0')])
    validate_last_for = IntegerField('有效期(单位:天)', validators=[NumberRange(min=1, max=None, message='有效期不能小于1天')])
    submit = SubmitField('确认')


class AlterCampaignForm(Form):
    description = StringField('方案名称', validators=[DataRequired()])
    consumer_pay = FloatField('付款金额', validators=[DataRequired(),
                                                  NumberRange(min=0, max=None, message='充值金额不能小于0')])
    into_card = FloatField('入卡金额', validators=[DataRequired(),
                                                  NumberRange(min=0, max=None, message='充值金额不能小于0')])
    validate_last_for = IntegerField('有效期(单位:天)', validators=[NumberRange(min=1, max=None, message='有效期不能小于1天')])
    submit = SubmitField('确认')


class RecordLookupForm(Form):
    datefrom = DateField('开始日期', validators=[DataRequired()])
    dateto = DateField('结束日期', validators=[DataRequired()])
    category = SelectField('类别', coerce=int, choices=[(1, '充值'), (2, '消费')])
    branchname = SelectField('门店', coerce=int)
    submit = SubmitField('查询')

    def __init__(self, *args, **kwargs):
        super(RecordLookupForm, self).__init__(*args, **kwargs)
        self.branchname.choices = [(user.id, user.branchname)
                                  for user in User.query.filter(User.role_id!=2).all()]
        self.branchname.choices.insert(0, (0, '全部门店'))
