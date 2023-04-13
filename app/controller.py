from app import app, factory, db, bcrypt, socketio
from app.dispatcher import trade_chain, user_active_trades, user_pending_trades, user_sid, sid_user
from app.models import User, Trade, trade_schema
from app.forms import RegistrationForm, LoginForm
from flask import render_template, jsonify, url_for, redirect, flash, request
from flask_login import login_user, current_user, logout_user, login_required






# If user is logged in redirect to /trade/btc else redirect to /home
@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    if current_user.is_authenticated:
        return redirect(url_for('tradebtc'))
    else:
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else  redirect(url_for('home'))
            else:
                flash('Login Unsuccessful. Please check email and password.', 'danger')
        return render_template('home.html', form=form)



# Bitcoin Trading UI Route
@app.route('/trade/btc')
@login_required
def tradebtc():
    try:
         user_active_trades[current_user.id]
    except KeyError:
        user_active_trades[current_user.id] = {'BTCUSDT':[], 'ETHUSDT': []}
        user_pending_trades[current_user.id] = {'BTCUSDT':[], 'ETHUSDT': []}

    pendings = [trade_schema.dump(pending) for pending in user_pending_trades[current_user.id]['BTCUSDT']]
    actives = [trade_schema.dump(active) for active in user_active_trades[current_user.id]['BTCUSDT']]  
    return render_template('tradebtc.html', actives=actives, pendings=pendings)

# Ethereum Trading UI Route
@app.route('/trade/eth')
@login_required
def tradeeth():
    try:
         print(current_user.id)
         user_active_trades[current_user.id]
    except KeyError:
        user_active_trades[current_user.id] = {'BTCUSDT':[], 'ETHUSDT': []}
        user_pending_trades[current_user.id] = {'BTCUSDT':[], 'ETHUSDT': []}

    pendings = [trade_schema.dump(pending) for pending in user_pending_trades[current_user.id]['ETHUSDT']]
    actives = [trade_schema.dump(active) for active in user_active_trades[current_user.id]['ETHUSDT']]  
    return render_template('tradeeth.html', actives=actives, pendings=pendings)


# Get historical candlestick data. AJAX call 
@app.route('/klines', methods=['POST', 'GET'])
def kline():
    if request.method == 'POST':
        response = request.form.to_dict()
        asset = factory.create_kline_object(list(response.keys())[0], list(response.values())[0])
        return jsonify(asset.get_historical_data())

# Get historical volume data. AJAX call 
@app.route('/volume', methods=['POST', 'GET'])
def volume():
    if request.method == 'POST':
        response = request.form.to_dict()
        asset = factory.create_kline_object(list(response.keys())[0], list(response.values())[0])
        return jsonify(asset.get_historical_data(volume=True))



# User Registration Route
@app.route("/register", methods = ['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tradebtc'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash(f'Account creation successful! You can now log in.', 'success')
        return redirect(url_for('home'))

    return render_template('register.html', title = 'Register', form = form )


# About Route
@app.route('/about')
def about():
    return render_template('about.html')


# Logout Route 
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# AJAX : Reset user assets
@app.route("/resetassets")
def reset_user_assets():
    current_user.assets = 1000
    current_user.available = 1000
    db.session.commit()
    return jsonify({"assets": current_user.assets})


# AJAX: Get trade when order is placed
@app.route("/loadtrade", methods=['POST'])
def load_trade():
    if request.method == 'POST':
        try:
            user_active_trades[current_user.id]
        except KeyError:
            user_active_trades[current_user.id] = {'BTCUSDT':[], 'ETHUSDT': []}
            user_pending_trades[current_user.id] = {'BTCUSDT':[], 'ETHUSDT': []}
        finally:
            trade = create_new_trade(request.form.to_dict(flat=True)) # Create the ORM object but do not add yet to the db
            trade_chain.add_to_queue(trade)
            cost = trade.qty*trade.open
            current_user.available = round(current_user.available - cost, 2)
            db.session.commit()
            return (jsonify({"available": current_user.available}), 201)


# AJAX: Trade is manually closed!
@app.route("/closetrade", methods=['POST'])
def close_trade():
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        id, status, contract, pnl = data.values()
        if status == 'active':
            to_close = next(trade for trade in user_active_trades[current_user.id][contract] if str(trade) == f'<Trade {id}>')
            user_active_trades[current_user.id][contract].remove(to_close)
        else: 
            to_close = next(trade for trade in user_pending_trades[current_user.id][contract] if str(trade) == f'<Trade {id}>')
            user_pending_trades[current_user.id][contract].remove(to_close)
        to_close.status = 'closed'
        cost= to_close.qty*to_close.open
        to_close.available = round((float(pnl)*cost)+cost, 2)
        to_close.assets= round(float(pnl)*cost, 2)
        db.session.commit()
        trade_chain.add_to_queue(to_close)
        return (jsonify({'available': to_close.available, 'total': to_close.assets}))




# Bind socket session to the user id when the client socket connects
@login_required
@socketio.on('connect')
def on_connection(sid):
    print(f' USER {current_user.id} CONNECTED!!!')   
    user_sid[current_user.id] = request.sid
    sid_user[request.sid] = current_user.id

   
# Delete the SID/UID mapping when a user disconnects
@socketio.on('disconnect')
def on_disconnection():
    print(f' USER {current_user.id} DISCONNECTED!!!')
    del user_sid[current_user.id]
    del sid_user[request.sid]

    

# Create a Trade ORM object but do not yet commit it
def create_new_trade(trade) -> Trade:
    newtrade = Trade(contract = trade['contract'], direction = trade['direction'], type = trade['type'], 
                        status = trade['status'], qty = float(trade['qty']), value = float(trade['value']),
                        open = float(trade['open']), close = float(trade['close']), leverage = float(trade['leverage']),
                        liq = float(trade['liq']), user_id = current_user.id)
    return newtrade

# # # If db service ends: activate this route and recreate db tables
# @app.route('/createdb')
# def create_db():
#     from datetime import datetime
#     db.create_all()
#     u1 = User(username = "Testing!", email = "testing@test.com", password = 'test')
#     db.session.add(u1)
#     db.session.commit()
#     return f'Succesfully added User {u1.username} at {datetime.utcnow()}'
