import sqlite3
def init_db():
    conn = sqlite3.connect('tutor_cache.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS cache(
        question TEXT PRIMARY KEY,
        answer TEXT
    )
    ''')
    conn.commit()
    conn.close()
def get_cached_answer(question):
    conn = sqlite3.connect('tutor_cache.db')
    c = conn.cursor()
    c.execute('SELECT answer FROM cache WHERE question = ?', (question,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None
def save_answer(question, answer):
    conn = sqlite3.connect('tutor_cache.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO cache (question, answer) VALUES (?, ?)',(question, answer))
    conn.commit()
    conn.close()


