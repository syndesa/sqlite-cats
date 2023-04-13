from app import db, login_manager, bcrypt, ma
from flask_login import UserMixin
from datetime import datetime





@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(12), unique = True, nullable = False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    assets = db.Column(db.Float, nullable=False, default=1000)
    available = db.Column(db.Float, nullable=False, default=1000)
    trades = db.relationship('Trade', backref='user', lazy=True)
    

    def __repr__(self) -> id:
        return str(self.id)


class Trade(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    contract = db.Column(db.String(10), nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    qty = db.Column(db.Float, nullable=False)
    value = db.Column(db.Float, nullable=False)
    open = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    leverage = db.Column(db.Float, nullable=False)
    pnl = db.Column(db.Float)
    liq = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default = datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    # Modify dunder behaviour for heapqpush
    def __lt__(self, t2):
        if t2.status == 'closed': return True 
        if self.status == 'active':
            if self.direction == 'Long':
                return float(self.liq) > float(t2.liq)
            else:
                return float(self.liq) < float(t2.liq)
        else:
            if self.direction == 'Long':
                return float(self.open) < float(t2.open)
            else:
                return float(self.open) > float(t2.open)

    # Modify str dunder to support string comparasion to Trade objects during /closetrade route
    def __str__(self) -> str:
        return f'<Trade {self.id}>'


    



#Used to access instance attributes e.g. trade_schema.dump(Trade)
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User


class TradeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Trade


user_schema = UserSchema()
trade_schema = TradeSchema()