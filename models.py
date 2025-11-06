from app import db

# Create the product model
class Product(db.Model):
    __tablename__ = "product"  # names the table in PostgreSQL

    id = db.Column(db.BigInteger, primary_key=True)
    product_code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
# attributes for calculating ROP
    current_stock = db.Column(db.Float, default=0.0)
    demand_per_day = db.Column(db.Float, default=0.0)
    lead_days = db.Column(db.Float, default=0.0)

    # ROP = demand_per_day * lead_days * 2.5  (includes 1.5x safety stock)
    def compute_rop(self):
        d = float(self.demand_per_day or 0.0)
        L = float(self.lead_days or 0.0)
        return round(d * L * 2.5, 2)
