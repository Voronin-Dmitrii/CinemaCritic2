from flask import Flask, render_template, redirect, url_for, flash, session, request
from flaskext.mysql import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'norm'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '1488'
app.config['MYSQL_DATABASE_DB'] = 'cinemacritic'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql = MySQL(app)
mysql.init_app(app)


@app.route('/')
def home():
    return redirect(url_for('movies'))


@app.route('/movies')
def movies():
    con = mysql.connect()
    cur = con.cursor()

    genre_filter = request.args.get('genre')
    sort_by = request.args.get('sort_by')
    page = int(request.args.get('page', 1))
    items_per_page = 50
    offset = (page - 1) * items_per_page

    query = '''
        SELECT 
            movies.movie_id, 
            movies.title, 
            movies.release_year, 
            movies.duration, 
            movies.poster_url, 
            movies.title_eng, 
            MAX(countries.name) AS country, 
            MAX(genres.name) AS genre, 
            MAX(directors.name) AS director,
            SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT actors.name ORDER BY actors.name ASC SEPARATOR ', '), ', ', 2) AS actors,
            movies.kp_rating
        FROM 
            movies
        LEFT JOIN 
            movie_countries ON movies.movie_id = movie_countries.movie_id
        LEFT JOIN 
            countries ON movie_countries.country_id = countries.country_id
        LEFT JOIN 
            movie_genres ON movies.movie_id = movie_genres.movie_id
        LEFT JOIN 
            genres ON movie_genres.genre_id = genres.genre_id
        LEFT JOIN 
            movie_directors ON movies.movie_id = movie_directors.movie_id
        LEFT JOIN 
            directors ON movie_directors.director_id = directors.director_id
        LEFT JOIN 
            movie_actors ON movies.movie_id = movie_actors.movie_id
        LEFT JOIN 
            actors ON movie_actors.actor_id = actors.actor_id
        WHERE 
            (%(genre_filter)s IS NULL OR %(genre_filter)s = '' OR genres.genre_id = %(genre_filter)s)
        GROUP BY 
            movies.movie_id
        '''

    if sort_by == 'title':
        query += ' ORDER BY movies.title'
    elif sort_by == 'release_year':
        query += ' ORDER BY movies.release_year'
    elif sort_by == 'average_rating':
        query += ' ORDER BY movies.kp_rating'
    else:
        query += ' ORDER BY movies.movie_id'

    query += ' LIMIT %(items_per_page)s OFFSET %(offset)s'

    cur.execute(query, {
        'genre_filter': genre_filter,
        'items_per_page': items_per_page,
        'offset': offset
    })

    movies = cur.fetchall()

    cur.execute('SELECT genre_id, name FROM genres')
    genres = cur.fetchall()

    cur.execute('SELECT COUNT(*) FROM movies')
    total_movies = cur.fetchone()[0]
    total_pages = (total_movies + items_per_page - 1) // items_per_page

    return render_template('movies.html', movies=movies, genres=genres, page=page, total_pages=total_pages,
                           genre=genre_filter, sort_by=sort_by)



@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    con = mysql.connect()
    cursor = con.cursor()
    cursor.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
    movie = cursor.fetchone()
    cursor.execute(
        "SELECT reviews.review_text, reviews.created_at, users.username FROM reviews JOIN users ON reviews.user_id = users.user_id WHERE reviews.movie_id = %s",
        (movie_id,))
    reviews = cursor.fetchall()
    return render_template('movie_detail.html', movie=movie, reviews=reviews)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        con = mysql.connect()
        cursor = con.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        con = mysql.connect()
        cursor = con.cursor()
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                       (username, email, password))
        con.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/review/<int:movie_id>', methods=['GET', 'POST'])
def review(movie_id):
    if 'user_id' not in session:
        flash('Please log in to leave a review', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        review_text = request.form['review_text']
        user_id = session['user_id']
        con = mysql.connect()
        cursor = con.cursor()
        cursor.execute("INSERT INTO reviews (movie_id, user_id, review_text) VALUES (%s, %s, %s)",
                       (movie_id, user_id, review_text))
        con.commit()
        return redirect(url_for('movie_detail', movie_id=movie_id))
    return render_template('review.html', movie_id=movie_id)


if __name__ == '__main__':
    app.run(debug=True)
