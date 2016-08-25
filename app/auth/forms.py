from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Length, DataRequired


class LoginForm(Form):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('密码', validators=[DataRequired()])
    login_host = StringField('', render_kw={"id": "hide_host", "type": "hidden"})
    remember_me = BooleanField('保持登录')
    submit = SubmitField('登录')


class RegUserForm(Form):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64)])
    reg_code = StringField('验证码', validators=[DataRequired()])
    reg_host = StringField('', render_kw={"id": "hide_host", "type": "hidden"})
    submit = SubmitField('提交')