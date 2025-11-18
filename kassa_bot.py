import os
import telebot
import sqlite3
from datetime import datetime
import time
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot ishlayapti! " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_flask():
    app.run(host='0.0.0.0', port=8080)

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8598689266:AAHNJ3FOu_n9peZil66Q3Tj3xRDDRnGBeqz')
bot = telebot.TeleBot(BOT_TOKEN)

conn = sqlite3.connect('kassa.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS products
               (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sales
               (id INTEGER PRIMARY KEY, product_id INTEGER, quantity INTEGER, 
                total_price INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

def initialize_products():
    products = [
        ("Gumma", 5000), ("Kartoshkali", 5000), ("Sasiskali", 8000),
        ("Xonim", 8000), ("Pepsi 0.5L", 9000), ("Pepsi 1L", 14000),
        ("Pepsi 1.5L", 17000), ("Ice tea 0.5L", 7000), ("Ice tea 1.25L", 13000),
        ("Bez gaz suv 0.5L", 5000), ("Maccofe", 7000), ("Qora kofe", 7000),
        ("Sous idish", 2000), ("Saboy idish", 2000), ("Limon choy", 7000),
        ("Malina choy", 7000), ("Novot choy", 7000)
    ]
    
    cursor.execute("DELETE FROM products")
    for product in products:
        cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", product)
    conn.commit()

initialize_products()

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = telebot.types.KeyboardButton('➕ Sotuv qo\'shish')
    btn2 = telebot.types.KeyboardButton('📥 Kirim')
    btn3 = telebot.types.KeyboardButton('📊 Hisobot')
    btn4 = telebot.types.KeyboardButton('⚙️ Sozlamalar')
    markup.add(btn1, btn2, btn3, btn4)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔄 Smena boshlandi!\nKassa botiga xush kelibsiz!", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == '➕ Sotuv qo\'shish')
def show_products(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    cursor.execute("SELECT id, name, price FROM products")
    products = cursor.fetchall()
    
    for product in products:
        btn = telebot.types.KeyboardButton(f"{product[1]} - {product[2]} so'm")
        markup.add(btn)
    
    back_btn = telebot.types.KeyboardButton('🔙 Orqaga')
    markup.add(back_btn)
    
    bot.send_message(message.chat.id, "Mahsulot tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda message: 'so\'m' in message.text)
def add_sale(message):
    try:
        product_name = message.text.split(' - ')[0]
        cursor.execute("SELECT id, price FROM products WHERE name = ?", (product_name,))
        product = cursor.fetchone()
        
        if product:
            msg = bot.send_message(message.chat.id, f"🔢 {product_name} sonini kiriting:\n(Masalan: 2)")
            bot.register_next_step_handler(msg, process_quantity, product[0], product[1], product_name)
        else:
            bot.send_message(message.chat.id, "❌ Mahsulot topilmadi!")
            
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Xato yuz berdi!")

def process_quantity(message, product_id, price, product_name):
    try:
        quantity = int(message.text)
        total_price = quantity * price
        
        cursor.execute("INSERT INTO sales (product_id, quantity, total_price) VALUES (?, ?, ?)", 
                      (product_id, quantity, total_price))
        conn.commit()
        
        bot.send_message(message.chat.id, 
                        f"✅ Sotuv qo'shildi!\n"
                        f"📦 {product_name}\n"
                        f"🔢 {quantity} ta\n"
                        f"💰 {total_price:,} so'm", 
                        reply_markup=main_menu())
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Son kiriting!")

@bot.message_handler(func=lambda message: message.text == '📊 Hisobot')
def show_report(message):
    cursor.execute('''SELECT p.name, SUM(s.quantity), SUM(s.total_price) 
                   FROM sales s JOIN products p ON s.product_id = p.id 
                   WHERE DATE(s.created_at) = DATE('now') 
                   GROUP BY p.name''')
    
    sales_data = cursor.fetchall()
    
    if not sales_data:
        bot.send_message(message.chat.id, "📊 Bugun hech qanday sotuv yo'q")
        return
    
    total_income = 0
    report_text = "📊 **KUNLIK HISOBOT**\n\n"
    
    for product in sales_data:
        report_text += f"• {product[0]}: {product[1]} ta - {product[2]:,} so'm\n"
        total_income += product[2]
    
    report_text += f"\n💰 **JAMI DAROMAD: {total_income:,} so'm**"
    
    bot.send_message(message.chat.id, report_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📥 Kirim')
def add_product(message):
    msg = bot.send_message(message.chat.id, "Yangi mahsulot nomi va narxini kiriting:\n(Masalan: Choy - 5000)")
    bot.register_next_step_handler(msg, process_new_product)

def process_new_product(message):
    try:
        data = message.text.split(' - ')
        if len(data) == 2:
            name = data[0].strip()
            price = int(data[1].strip())
            
            cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
            conn.commit()
            
            bot.send_message(message.chat.id, f"✅ Yangi mahsulot qo'shildi: {name} - {price} so'm", 
                           reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, "❌ Noto'g'ri format! Masalan: Choy - 5000")
    except:
        bot.send_message(message.chat.id, "❌ Xato yuz berdi!")

@bot.message_handler(func=lambda message: message.text == '⚙️ Sozlamalar')
def settings(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton('📦 Mahsulotlar ro\'yxati')
    btn2 = telebot.types.KeyboardButton('🔄 Smenani yangilash')
    btn3 = telebot.types.KeyboardButton('🔙 Orqaga')
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(message.chat.id, "Sozlamalar:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📦 Mahsulotlar ro\'yxati')
def product_list(message):
    cursor.execute("SELECT name, price FROM products")
    products = cursor.fetchall()
    
    product_text = "📦 **MAHSULOTLAR RO'YXATI**\n\n"
    for product in products:
        product_text += f"• {product[0]} - {product[1]:,} so'm\n"
    
    bot.send_message(message.chat.id, product_text, parse_mode='Markdown', reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == '🔄 Smenani yangilash')
def reset_shift(message):
    cursor.execute("DELETE FROM sales")
    conn.commit()
    bot.send_message(message.chat.id, "✅ Smena yangilandi! Barcha sotuvlar tozalandi.", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == '🔙 Orqaga')
def back_to_main(message):
    bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu())

def run_bot():
    while True:
        try:
            print("Bot ishga tushdi...")
            bot.polling(none_stop=True, interval=2, timeout=60)
        except Exception as e:
            print(f"Xato: {e}")
            time.sleep(10)
            continue

if __name__ == "__main__":
    run_bot()
