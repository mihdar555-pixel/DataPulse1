from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from analytics import process_file, generate_sample_template
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///datapulse.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'xls'}

# ── Models ────────────────────────────────────────────────────────────────────

class Import(db.Model):
    __tablename__ = 'imports'
    id              = db.Column(db.Integer, primary_key=True)
    original_name   = db.Column(db.String(255), nullable=False)
    file_extension  = db.Column(db.String(10),  nullable=False)
    file_size_bytes = db.Column(db.Integer)
    total_rows      = db.Column(db.Integer)
    valid_rows      = db.Column(db.Integer)
    status          = db.Column(db.String(20), default='pending')
    error_message   = db.Column(db.Text)
    imported_at     = db.Column(db.DateTime, default=datetime.utcnow)
    kpi             = db.relationship('KpiSnapshot', backref='import_ref', uselist=False, cascade='all, delete-orphan')
    status_agg      = db.relationship('AggStatus',   backref='import_ref', cascade='all, delete-orphan')
    trend_agg       = db.relationship('AggTrend',    backref='import_ref', cascade='all, delete-orphan')

class KpiSnapshot(db.Model):
    __tablename__ = 'kpi_snapshots'
    id                = db.Column(db.Integer, primary_key=True)
    import_id         = db.Column(db.Integer, db.ForeignKey('imports.id'), unique=True)
    chiffre_affaires  = db.Column(db.Float)
    total_commandes   = db.Column(db.Integer)
    commandes_livrees = db.Column(db.Integer)
    panier_moyen      = db.Column(db.Float)
    taux_livraison    = db.Column(db.Float)
    date_min          = db.Column(db.String(20))
    date_max          = db.Column(db.String(20))
    computed_at       = db.Column(db.DateTime, default=datetime.utcnow)

class AggStatus(db.Model):
    __tablename__ = 'agg_status'
    id          = db.Column(db.Integer, primary_key=True)
    import_id   = db.Column(db.Integer, db.ForeignKey('imports.id'))
    label       = db.Column(db.String(50))
    order_count = db.Column(db.Integer)

class AggTrend(db.Model):
    __tablename__ = 'agg_trend'
    id        = db.Column(db.Integer, primary_key=True)
    import_id = db.Column(db.Integer, db.ForeignKey('imports.id'))
    day       = db.Column(db.String(20))
    revenue   = db.Column(db.Float)

# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/history')
def history():
    imports = Import.query.order_by(Import.imported_at.desc()).limit(20).all()
    result = []
    for imp in imports:
        entry = {
            'id':          imp.id,
            'name':        imp.original_name,
            'status':      imp.status,
            'total_rows':  imp.total_rows,
            'imported_at': imp.imported_at.strftime('%d/%m/%Y %H:%M') if imp.imported_at else '',
        }
        if imp.kpi:
            entry['chiffre_affaires'] = imp.kpi.chiffre_affaires
            entry['taux_livraison']   = imp.kpi.taux_livraison
        result.append(entry)
    return jsonify(result)

@app.route('/import/<int:import_id>')
def get_import(import_id):
    imp = Import.query.get_or_404(import_id)
    if not imp.kpi:
        return jsonify({'error': 'Données non disponibles'}), 404
    kpi = imp.kpi
    status_data = {
        'labels': [s.label       for s in imp.status_agg],
        'values': [s.order_count for s in imp.status_agg],
    }
    trend_data = {
        'labels': [t.day     for t in sorted(imp.trend_agg, key=lambda x: x.day)],
        'values': [t.revenue for t in sorted(imp.trend_agg, key=lambda x: x.day)],
    }
    return jsonify({
        'kpis': {
            'chiffre_affaires': kpi.chiffre_affaires,
            'total_commandes':  kpi.total_commandes,
            'panier_moyen':     kpi.panier_moyen,
            'taux_livraison':   kpi.taux_livraison,
        },
        'status_breakdown': status_data,
        'trend_data':       trend_data,
        'total_rows':       imp.total_rows,
        'import_name':      imp.original_name,
        'import_date':      imp.imported_at.strftime('%d/%m/%Y %H:%M') if imp.imported_at else '',
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier reçu.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nom de fichier vide.'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Format non supporté. Utilisez .xlsx, .xls ou .csv'}), 400

    imp = Import(
        original_name   = file.filename,
        file_extension  = file.filename.rsplit('.', 1)[1].lower(),
        file_size_bytes = 0,
        status          = 'processing',
    )
    db.session.add(imp)
    db.session.flush()

    try:
        file_bytes = file.read()
        imp.file_size_bytes = len(file_bytes)
        result = process_file(file_bytes, imp.file_extension)

        kpi = KpiSnapshot(
            import_id         = imp.id,
            chiffre_affaires  = result['kpis']['chiffre_affaires'],
            total_commandes   = result['kpis']['total_commandes'],
            commandes_livrees = int(result['kpis']['total_commandes'] * result['kpis']['taux_livraison'] / 100),
            panier_moyen      = result['kpis']['panier_moyen'],
            taux_livraison    = result['kpis']['taux_livraison'],
            date_min          = result['trend_data']['labels'][0]  if result['trend_data']['labels'] else None,
            date_max          = result['trend_data']['labels'][-1] if result['trend_data']['labels'] else None,
        )
        db.session.add(kpi)

        for label, count in zip(result['status_breakdown']['labels'], result['status_breakdown']['values']):
            db.session.add(AggStatus(import_id=imp.id, label=label, order_count=count))

        for day, rev in zip(result['trend_data']['labels'], result['trend_data']['values']):
            db.session.add(AggTrend(import_id=imp.id, day=day, revenue=rev))

        imp.status     = 'success'
        imp.total_rows = result['total_rows']
        imp.valid_rows = result['total_rows']
        db.session.commit()

        return jsonify({
            'import_id':        imp.id,
            'kpis':             result['kpis'],
            'status_breakdown': result['status_breakdown'],
            'trend_data':       result['trend_data'],
            'total_rows':       result['total_rows'],
            'import_name':      imp.original_name,
            'import_date':      imp.imported_at.strftime('%d/%m/%Y %H:%M'),
        })

    except ValueError as e:
        db.session.rollback()
        imp.status = 'error'; imp.error_message = str(e); db.session.commit()
        return jsonify({'error': str(e)}), 422
    except Exception as e:
        db.session.rollback()
        imp.status = 'error'; imp.error_message = str(e); db.session.commit()
        return jsonify({'error': f'Erreur de traitement: {str(e)}'}), 500

@app.route('/template')
def download_template():
    output = generate_sample_template()
    return send_file(output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name='template_ventes.xlsx')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
