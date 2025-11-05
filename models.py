from datetime import datetime
from app import db

class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.BigInteger, primary_key=True)
    product_code = db.Column(db.String(64), unique=True, nullable=False)  # user-entered unique ID
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)  # optional

    current_stock = db.Column(db.Float, default=0.0)

    demand_per_day = db.Column(db.Float, default=0.0)
    lead_days = db.Column(db.Float, default=0.0)

    location = db.Column(db.String(120))
    supplier_name = db.Column(db.String(120))

    # One-time low-stock notify flag
    notified_low = db.Column(db.Boolean, default=False, nullable=False)

    movements = db.relationship("StockMovement", backref="product", cascade="all, delete-orphan")

    # ROP = dpd * lead_days * 2.5 (includes 1.5x safety stock)
    def compute_rop(self):
        d = float(self.demand_per_day or 0.0)
        L = float(self.lead_days or 0.0)
        rop = d * L * 2.5
        inv_pos = float(self.current_stock or 0.0)  # no on_order in this iteration

        suggested = max(rop - inv_pos, 0.0)
        below = inv_pos <= rop

        return {
            "ROP": round(rop, 2),
            "inventory_position": round(inv_pos, 2),
            "suggested_order_qty": round(suggested, 2),
            "below": below,
        }

    def refresh_notification_state(self):
        """Clear one-time notification flag if recovered above ROP."""
        m = self.compute_rop()
        if not m["below"] and self.notified_low:
            self.notified_low = False


class StockMovement(db.Model):
    __tablename__ = "stock_movement"

    id = db.Column(db.BigInteger, primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    qty_change = db.Column(db.Float, nullable=False)     # +receipt, -issue
    reason = db.Column(db.String(32), default="ADJUSTMENT")
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def apply_to_product(self):
        self.product.current_stock = (self.product.current_stock or 0) + self.qty_change
