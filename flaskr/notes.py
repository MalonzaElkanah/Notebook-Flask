from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('notes', __name__)


# - index
@bp.route('/')
@login_required
def index():
    db = get_db()
    # most recent
    recent_notes = db.execute(
        'SELECT n.id, title, content, created, status'
        ' FROM journal n JOIN category c ON n.category_id = c.id'
        ' WHERE n.user_id = ?'
        ' ORDER BY created DESC',
        (g.user['id'],)
    ).fetchall()

    # most clicked
    popular_notes = db.execute(
        'SELECT n.id, title, content, created, status'
        ' FROM journal n JOIN category c ON n.category_id = c.id'
        ' WHERE n.user_id = ?'
        ' ORDER BY clicks DESC',
        (g.user['id'],)
    ).fetchall()

    return render_template('notes/index.html', recent_notes=recent_notes, popular_notes=popular_notes, 
        categories = my_categories(), series = my_series()
    ) 


# - create category
@bp.route('/category/create', methods=['GET', 'POST'])
@login_required
def create_category():
    if request.method == 'POST':
        name = request.form['name']
        error = None

        if not name:
            error = 'Category Name is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO category (name, user_id)'
                ' VALUES (?, ?)',
                (name, g.user['id'])
            )
            db.commit()
            flash('Category Created')
            return redirect(url_for('notes.create_note'))

    return render_template('notes/create_category.html', page="Create Category")


# - create series
@bp.route('/series/create', methods=['GET', 'POST'])
@login_required
def create_series():
    if request.method == 'POST':
        name = request.form['name']
        error = None

        if not name:
            error = 'Series Name is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO series (name, user_id)'
                ' VALUES (?, ?)',
                (name, g.user['id'])
            )
            db.commit()
            flash('Series Created')
            return redirect(url_for('notes.create_note'))

    return render_template('notes/create_category.html', page="Create Series")


# - create note
@bp.route('/notes/create', methods=('GET', 'POST'))
@login_required
def create_note():
    if request.method == 'POST':
        # Get title, category_id, series_id, image, content, tags
        title = request.form.get('title', None)
        category_id = request.form.get('category', None) 
        series_id = request.form.get('series', None)
        content = request.form.get('content', '[None]') 
        tags = request.form.get('tags', 'new,')
        # Upload Image and get filename
        image = None
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO journal (title, category_id, series_id, image, content, tags, user_id)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                (title, category_id, series_id, image, content, tags, g.user['id'])
            )
            db.commit()
            return redirect(url_for('notes.notes'))

    return render_template('notes/create_note.html', categories = my_categories(), series = my_series(), 
        page="Create Note")


# - update note
@bp.route('/notes/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update_note(id):
    note = get_note(id)
    if request.method == 'POST':
        # Get title, category_id, series_id, image, content, tags
        title = request.form.get('title', None)
        category_id = request.form.get('category', None) 
        series_id = request.form.get('series', None)
        content = request.form.get('content', '[None]') 
        tags = request.form.get('tags', 'new,')
        # Upload Image and get filename
        image = None
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE journal SET title = ?, category_id = ?, series_id = ?, content = ?, tags = ?, image = ?'
                ' WHERE id = ?',
                (title, category_id, series_id, content, tags, image, id)
            )
            db.commit()
            flash("{} Note updated".formart(title))

            return redirect(url_for('notes.note', id=id))

    return render_template('notes/create_note.html', note=note,  categories = my_categories(), 
        series = my_series(), page="Update Note: {}".format(note['title']))



# - change note status (Draft, Publish, Archive, Trash)
@bp.route('/notes/<int:id>/status')
@login_required
def update_status(id, status):
    # get note and check if note belong to request user
    note = get_note(id)
    if status.capitalize() in ['DRAFT', 'PUBLISH', 'ARCHIVE', 'TRASH']:
        db = get_db()
        db.execute('UPDATE journal SET status = ? WHERE id = ?', (status.capitalize(), id))
        db.commit()
        flash("Status updated")
    else:    
        flash("Status cannot be {}.".format(status.capitalize()))

    return redirect('notes.note', id=id)


# - delete note
@bp.route('/notes/<int:id>/delete')
@login_required
def delete_note(id):
    get_note(id)
    db = get_db()
    db.execute('DELETE FROM journal WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('notes.index'))


# - view all notes
@bp.route('/notes')
@login_required
def notes():
    notes = get_db().execute(
        'SELECT n.id, n.user_id, n.title, n.image, n.created, n.status, c.name, n.series_id, n.tags'
        ' FROM journal n JOIN category c ON n.category_id = c.id'
        ' WHERE n.user_id = ?',
        (g.user['id'],)
    ).fetchall()

    return render_template('notes/notes.html', notes=notes, page="All Notes")


# - view series notes
@bp.route('/notes/<int:series_id>/series')
@login_required
def series_notes(series_id):
    series = get_db().execute(
        'SELECT name, user_id FROM series WHERE id = ?',
        (series_id,)
    ).fetchone()

    # check if category exists and belong to user
    if series is None:
        abort(404, f"Series doesn't exist.")
    elif series['user_id'] != g.user['id']:
        abort(403)    
    else:
        notes = get_db().execute(
            'SELECT n.id, n.user_id, n.title, n.image, n.created, n.status, c.name, n.series_id, n.tags'
            ' FROM journal n JOIN category c ON n.category_id = c.id'
            ' WHERE n.series_id = ?',
            (series_id,)
        ).fetchall()

        status = "Series: {} Notes".format(series['name'])

        return render_template('notes/notes.html', notes=notes, page=status)


# - view category notes
@bp.route('/notes/<int:category_id>/category')
@login_required
def category_notes(category_id):
    category = get_db().execute(
        'SELECT name, user_id FROM category WHERE id = ?',
        (category_id,)
    ).fetchone()

    # check if category exists and belong to user
    if category is None:
        abort(404, f"Category doesn't exist.")
    elif category['user_id'] != g.user['id']:
        abort(403)    
    else:
        notes = get_db().execute(
            'SELECT n.id, n.user_id, n.title, n.image, n.created, n.status, c.name, n.series_id, n.tags'
            ' FROM journal n JOIN category c ON n.category_id = c.id'
            ' WHERE n.category_id = ?',
            (category_id,)
        ).fetchall()

        status = "Category: {} Notes".format(category['name'])

        return render_template('notes/notes.html', notes=notes, page=status)


# - view specific note
@bp.route('/notes/<int:id>/note')
@login_required
def note(id):
    note = get_note(id)
    return render_template('notes/note.html', note=note)


def get_note(id, check_user=True):
    note = get_db().execute(
        'SELECT n.*, c.name'
        ' FROM journal n JOIN category c ON n.category_id = c.id'
        ' WHERE n.id = ?',
        (id,)
    ).fetchone()

    # Check if List Exist and belongs to request Owner
    if note is None:
        abort(404, f"Post id {id} doesn't exist.")
    elif check_user and note['user_id'] != g.user['id']:
        abort(403)

    return note


def my_series(check_user=True):
    series = get_db().execute(
        'SELECT name, id FROM series WHERE user_id = ?',
        (g.user['id'],)
    ).fetchall() 
    
    return series


def my_categories(check_user=True):
    categories = get_db().execute(
        'SELECT name, id FROM category WHERE user_id = ?',
        (g.user['id'],)
    ).fetchall()   

    return categories
