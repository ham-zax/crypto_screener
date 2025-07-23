from src.database import db

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hot_sector = db.Column(db.String(100), nullable=True)
    value_proposition = db.Column(db.Text, nullable=True)
    backing_team = db.Column(db.Text, nullable=True)
    initial_float = db.Column(db.String(100), nullable=True)
    real_utility = db.Column(db.Text, nullable=True)
    fair_launch_vesting = db.Column(db.Text, nullable=True)
    macro_accumulation_divergence = db.Column(db.String(100), nullable=True)
    spot_cvd_ma_cvd = db.Column(db.String(100), nullable=True)
    market_structure_shift_retest = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Project {self.name}>'


