from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import mysql.connector.pooling
from contextlib import contextmanager

pool =  mysql.connector.pooling.MySQLConnectionPool(
        pool_name="my_pool",
        pool_size=5,
        pool_reset_session=True,
        host='127.0.0.1',
        user='root',
        password='',
        database='ap_dolt',
)

app = Flask(__name__)
CORS(app)

@contextmanager
def get_cursor():
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        connection.commit()
        connection.close()

@app.route('/user_cards/<int:user_id>')
def get_user_cards(user_id):
    query = '''
    SELECT 
        user_cards.id,
        user_cards.user_id,
        user_cards.card_id,
        user_cards.active,
        user_cards.due,
        user_cards.last_interval,
        user_cards.deleted,
        flashcards.question,
        flashcards.answer,
        topics.name AS topic_name
    FROM 
        user_cards
    JOIN
        flashcards ON user_cards.card_id = flashcards.id
    JOIN
        topics ON flashcards.topic_id = topics.id
    WHERE
        user_cards.user_id = %s;
    '''
    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        return jsonify(results)


@contextmanager
def get_cursor():
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        connection.close()

@app.route('/add_user', methods=['POST'])
def add_user():
    user_id = request.json['user_id']
    
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM topics")
        topic_ids = [row[0] for row in cursor.fetchall()]

        for topic_id in topic_ids:
            cursor.execute("""
                INSERT INTO user_topics (user_id, topic_id, quiz_taken, reading_done, added)
                VALUES (%s, %s, 0, 0, 0)
            """, (user_id, topic_id))

    return jsonify({"status": "success"})

@app.route('/add_topic', methods=['POST'])
def add_topic():
    user_id = request.json['user_id']
    topic_id = request.json['topic_id']
    today = datetime.date.today()

    with get_cursor() as cursor:
        cursor.execute("""
            UPDATE user_topics
            SET added = 1
            WHERE user_id = %s AND topic_id = %s
        """, (user_id, topic_id))

        cursor.execute("""
            SELECT id FROM flashcards
            WHERE topic_id = %s
        """, (topic_id, ))
        flashcard_ids = [row[0] for row in cursor.fetchall()]

        for card_id in flashcard_ids:
            cursor.execute("""
                INSERT INTO user_cards (user_id, card_id, due_date, last_seen, active, deleted)
                VALUES (%s, %s, %s, %s, 1, 0)
            """, (user_id, card_id, today, today))
        

    return jsonify({"status": "success"})

@app.route('/get_mc_questions/<int:topic_id>')
def get_mc_questions(topic_id):
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM MC
            WHERE topic_id = %s
        """, (topic_id,))
        results = cursor.fetchall()
    
    return jsonify(results)

@app.route('/delete_card', methods=['POST'])
def delete_card():
    user_id = request.json['user_id']
    card_id = request.json['card_id']

    with get_cursor() as cursor:
        cursor.execute("""
            UPDATE user_cards
            SET deleted = 1
            WHERE user_id = %s AND card_id = %s
        """, (user_id, card_id))

    return jsonify({"status": "success"})

@app.route('/review_card', methods=['POST'])
def review_card():
    user_id = request.json['user_id']
    card_id = request.json['card_id']
    due_date = request.json['due_date']
    last_seen = request.json['last_seen']

    with get_cursor() as cursor:
        cursor.execute("""
            UPDATE user_cards
            SET due_date = %s, last_seen = %s
            WHERE user_id = %s AND card_id = %s
        """, (due_date, last_seen, user_id, card_id))

    return jsonify({"status": "success"})

@app.route('/get_topics')
def get_topics():
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM topics")
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        topics = [dict(zip(columns, row)) for row in results]

    return jsonify(topics)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
