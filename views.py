from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from models import Product

bp = Blueprint("main", __name__) # allows for the calling of all models at once in app.py

# getting string data from forms
def get_str(name, default=""):
    return (request.form.get(name, default) or "").strip()
# getting numerical data from forms
def get_float(name, default=0.0):
    try:
        return float(request.form.get(name, default))
    except Exception:
        return default

# product route READ

@bp.route("/products")
def products():
    q = (request.args.get("q") or "").strip()
    query = Product.query
    if q:
        like = f"%{q}%"
        query = query.filter((Product.product_code.ilike(like)) | (Product.name.ilike(like)))
    items = query.order_by(Product.name.asc()).all()
    return render_template("products.html", items=items, q=q)

# Create a new product CREATE
@bp.route("/products/new", methods=["GET", "POST"])
def product_new():
    if request.method == "POST":
        p = Product(
            product_code=get_str("product_code"),
            name=get_str("name"),
            description=get_str("description"),
            current_stock=get_float("current_stock"),
            demand_per_day=get_float("demand_per_day"),
            lead_days=get_float("lead_days"),
        )
        if not p.product_code or not p.name:
            flash("Product Code and Name are required.", "danger") # validating the new product
            return redirect(url_for("main.product_new"))
        db.session.add(p)
        db.session.commit()
        flash("Product created.", "success")
        return redirect(url_for("main.products"))
    return render_template("product_form.html", item=None)

# Edit products UPDATE
@bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
def product_edit(pid):
    p = Product.query.get_or_404(pid)
    if request.method == "POST":
        p.product_code = get_str("product_code") or p.product_code
        p.name = get_str("name") or p.name
        p.description = get_str("description")
        p.current_stock = get_float("current_stock", p.current_stock)
        p.demand_per_day = get_float("demand_per_day", p.demand_per_day)
        p.lead_days = get_float("lead_days", p.lead_days)
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("main.products"))
    return render_template("product_form.html", item=p)

# Delete Products DELETE
@bp.route("/products/<int:pid>/delete", methods=["POST"])
def product_delete(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Product deleted.", "warning")
    return redirect(url_for("main.products"))
