from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from models import Product, StockMovement

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

# product route READ is3312 project 2024, Chat GPT

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
# ChatGPT - see documentation for conversation
@bp.route("/products/<int:pid>/add_stock", methods=["POST"])
def product_add_stock(pid):
    p = Product.query.get_or_404(pid)
    qty = get_float("qty", 0.0)

    if qty <=0:
        flash("Quantity must be greater than zero", "danger")
        return redirect(url_for("main.product_edit", pid=pid))

    p.current_stock = (p.current_stock or 0.0) + qty

    rop = p.compute_rop()
    if p.current_stock >= rop and p.notified_low:
        p.notified_low = False


    m= StockMovement(product_id=pid, movement_type="Delivery", qty_change=qty)
    db.session.add(m)
    db.session.commit()
    flash("Stock Updated", "Success")
    return redirect(url_for("main.product_edit", pid=pid))

# issue stock issues resolved by ChatGPT
@bp.route("/products/<int:pid>/issue_stock", methods=["POST"])
def product_issue_stock(pid):
    """Issue stock to a factory location from the product form."""
    p = Product.query.get_or_404(pid)

    # read form values
    qty = get_float("qty", 0.0)
    location = get_str("location")

    # validation: qty must be > 0
    if qty <= 0:
        flash("Quantity must be greater than zero.", "danger")
        return redirect(url_for("main.product_edit", pid=pid))

    # validation: cannot issue more than current stock
    if qty > (p.current_stock or 0.0):
        flash("Not enough stock to issue.", "danger")
        return redirect(url_for("main.product_edit", pid=pid))

    # update current stock
    before_stock = p.current_stock or 0.0
    p.current_stock = before_stock - qty

    rop = p.compute_rop()
    if p.current_stock< rop:
        flash(f"Warning: stock for {p.name} is below ROP. "f"Current stock: {p.current_stock}.")

    # record stock movement
    m = StockMovement(product_id=pid, movement_type="ISSUE", qty_change=-qty, location=location)

    db.session.add(m)
    db.session.commit()

    flash("Stock issued and updated.", "success")
    return redirect(url_for("main.product_edit", pid=pid))


@bp.route("/low-stock-dashboard")
def low_stock_dashboard():
    products = Product.query.order_by(Product.name.asc()).all()
    rows = []
    for p in products:
        rop = p.compute_rop()
        current = float(p.current_stock or 0.0)
        threshold = rop + (rop * 0.125)

        if current <= threshold:
            rows.append({"product": p, "current": current, "rop": rop, "threshold": threshold, "below_rop": current < rop})

    return render_template("low_stock_dashboard.html", rows=rows)


    db.session.add(m)
    db.session.commit()
    flash("Stock issued and updated.", "success")
    return redirect(url_for("main.product_edit", pid=pid))