from flask import Blueprint, render_template, redirect, url_for, request, jsonify, abort, g
from typing import Tuple
from api.queries import (
    list_books as query_list_books,
    count_books as query_count_books,
    get_book_detail,
    get_book_contributors,
    get_book_subjects,
    get_book_prices,
    get_push_status,
)

books_bp = Blueprint("books", __name__)


@books_bp.route("/")
def index():
    return redirect(url_for("books.list_books_view"))


@books_bp.route("/books")
def list_books_view():
    try:
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1

        q = request.args.get("q", "")

        books = query_list_books(g.db, page, 20, q)
        total = query_count_books(g.db, q)

        pages = (total + 19) // 20

        return render_template(
            "books_list.html",
            books=books,
            page=page,
            per_page=20,
            total=total,
            pages=pages,
            search_query=q,
        )
    except Exception:
        return render_template("error.html", status=503, message="Database unavailable — please try again later"), 503


@books_bp.route("/books/<int:book_id>")
def book_detail(book_id: int) -> str:
    try:
        book = get_book_detail(g.db, book_id)
        if not book:
            return render_template("error.html", status=404, message="Book not found"), 404

        contributors = get_book_contributors(g.db, book_id)
        subjects = get_book_subjects(g.db, book_id)
        prices = get_book_prices(g.db, book_id)
        push_status = get_push_status(g.db, book_id)

        return render_template(
            "book_detail.html",
            book=book,
            contributors=contributors,
            subjects=subjects,
            prices=prices,
            push_status=push_status,
        )
    except Exception:
        return render_template("error.html", status=503, message="Database unavailable — please try again later"), 503


@books_bp.route("/api/books")
def api_books():
    try:
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1

        q = request.args.get("q", "")

        books = query_list_books(g.db, page, 20, q)
        total = query_count_books(g.db, q)

        return jsonify(
            {
                "books": books,
                "page": page,
                "per_page": 20,
                "total": total,
            }
        )
    except Exception:
        return jsonify({"error": "Database unavailable"}), 503


@books_bp.route("/api/books/search")
def api_search():
    try:
        q = request.args.get("q", "")
        page = 1

        books = query_list_books(g.db, page, 20, q)

        if not books:
            return '<tr><td colspan="10" class="text-center">No books found matching your search</td></tr>'

        return render_template("partials/book_rows.html", books=books)
    except Exception:
        return "", 503


@books_bp.route("/api/books/<int:book_id>")
def api_book_detail(book_id: int):
    try:
        book = get_book_detail(g.db, book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404

        contributors = get_book_contributors(g.db, book_id)
        subjects = get_book_subjects(g.db, book_id)
        prices = get_book_prices(g.db, book_id)
        push_status = get_push_status(g.db, book_id)

        return jsonify(
            {
                "book": book,
                "contributors": contributors,
                "subjects": subjects,
                "prices": prices,
                "push_status": push_status,
            }
        )
    except Exception:
        return jsonify({"error": "Database unavailable"}), 503
