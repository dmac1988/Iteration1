from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from models import Product, StockMovement

bp = Blueprint("main", __name__)

# --- helpers ---
def get_str(name, default=""):
    return (request.form.get(name, default) or "").strip()

def get_float(name, default=0.0):
    try:
        return float(request.form.get(name, default))
    except Exception:
        return default

# ---------------- Products ----------------
@bp.route("/products")
def products():
    q = (request.args.get("q") or "").strip()
    query = Product.query
    if q:
        like = f"%{q}%"
        query = query.filter((Product.product_code.ilike(like)) | (Product.name.ilike(like)))
    items = query.order_by(Product.name.asc()).all()

    # auto-reset notification flags for recovered items
    changed = False
    for p in items:
        before = p.notified_low
        p.refresh_notification_state()
        if before and not p.notified_low:
            changed = True
    if changed:
        db.session.commit()

    return render_template("products.html", items=items, q=q)

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
            location=get_str("location"),
            supplier_name=get_str("supplier_name"),
        )
        if not p.product_code or not p.name:
            flash("Product Code and Name are required.", "danger")
            return redirect(url_for("main.product_new"))
        db.session.add(p)
        db.session.commit()
        flash("Product created.", "success")
        return redirect(url_for("main.products"))
    return render_template("product_form.html", item=None)

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
        p.location = get_str("location")
        p.supplier_name = get_str("supplier_name")
        p.refresh_notification_state()
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("main.products"))
    return render_template("product_form.html", item=p)

@bp.route("/products/<int:pid>/delete", methods=["POST"])
def product_delete(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Product deleted.", "warning")
    return redirect(url_for("main.products"))

# ---------------- Stock ----------------
@bp.route("/products/<int:pid>/stock")
def stock_movements(pid):
    p = Product.query.get_or_404(pid)
    moves = StockMovement.query.filter_by(product_id=p.id).order_by(StockMovement.created_at.desc()).all()
    m = p.compute_rop()
    return render_template("stock_movements.html", item=p, moves=moves, m=m)

@bp.route("/products/<int:pid>/stock/add", methods=["POST"])
def stock_add(pid):
    p = Product.query.get_or_404(pid)
    qty = get_float("qty")
    note = get_str("note")
    if qty <= 0:
        flash("Quantity must be positive.", "danger")
        return redirect(url_for("main.stock_movements", pid=pid))
    mv = StockMovement(product=p, qty_change=qty, reason="RECEIPT", note=note)
    db.session.add(mv)
    mv.apply_to_product()
    p.refresh_notification_state()
    db.session.commit()
    flash("Stock added.", "success")
    return redirect(url_for("main.stock_movements", pid=pid))

@bp.route("/products/<int:pid>/stock/issue", methods=["POST"])
def stock_issue(pid):
    p = Product.query.get_or_404(pid)
    qty = get_float("qty")
    note = get_str("note")
    if qty <= 0:
        flash("Quantity must be positive.", "danger")
        return redirect(url_for("main.stock_movements", pid=pid))
    mv = StockMovement(product=p, qty_change=-qty, reason="ISSUE", note=note)
    db.session.add(mv)
    mv.apply_to_product()
    p.refresh_notification_state()
    db.session.commit()
    flash("Stock issued.", "success")
    return redirect(url_for("main.stock_movements", pid=pid))

# Delete a movement (reverse its effect)
@bp.route("/stock/<int:mid>/delete", methods=["POST"], endpoint="movement_delete")
def movement_delete(mid):
    mv = StockMovement.query.get_or_404(mid)
    p = mv.product
    p.current_stock = (p.current_stock or 0) - mv.qty_change
    db.session.delete(mv)
    p.refresh_notification_state()
    db.session.commit()
    flash("Movement deleted.", "warning")
    return redirect(url_for("main.stock_movements", pid=p.id))

# -------- One-time low-stock notification API --------
@bp.route("/api/low-stock-once", methods=["POST"])
def low_stock_once():
    """
    Return products that are below ROP AND not yet notified.
    Mark them notified so they won't show again until they recover above ROP.
    """
    items = Product.query.all()
    to_notify = []
    for p in items:
        m = p.compute_rop()
        if m["below"] and not p.notified_low:
            to_notify.append({
                "product_code": p.product_code,
                "name": p.name,
                "inventory_position": m["inventory_position"],
                "ROP": m["ROP"],
                "suggested_order_qty": m["suggested_order_qty"],
            })
            p.notified_low = True
    if to_notify:
        db.session.commit()
    return jsonify(to_notify)
