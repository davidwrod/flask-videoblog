from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class CadastroForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    username = StringField('Nome de usuário', validators=[DataRequired(), Length(min=5, max=20)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=8, max=128)])
    password_confirmation = PasswordField('Confirme sua senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem coincidir')])
    terms = BooleanField('Eu concordo com os Termos de Serviço e a Política de Privacidade', validators=[DataRequired()])
    submit = SubmitField('Criar Conta')

class LoginForm(FlaskForm):
    username = StringField('Nome de usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar de mim')

class EmptyForm(FlaskForm):
    pass
