from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import DeliveryZone

bp = Blueprint('admin_delivery', __name__, url_prefix='/admin/delivery')

@bp.route('/')
@login_required
def index():
    zones = DeliveryZone.query.all()
    return render_template('admin/delivery_zones.html', zones=zones)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        fee  = int(request.form.get('fee'))
        eta = request.form.get("eta", "").strip()
        if DeliveryZone.query.filter_by(name=name).first():
            flash('Zone already exists', 'warning')
            return redirect(url_for('admin_delivery.add'))
        db.session.add(DeliveryZone(name=name, fee=fee, eta=eta))
        db.session.commit()
        flash('Zone added', 'success')
        return redirect(url_for('admin_delivery.index'))
    return render_template('admin/delivery_zone_form.html', title='Add Zone')




@bp.route('/edit/<int:zone_id>', methods=['GET', 'POST'])
@login_required
def edit(zone_id):
    zone = DeliveryZone.query.get_or_404(zone_id)
    if request.method == 'POST':
        zone.name = request.form.get('name').strip()
        zone.fee  = int(request.form.get('fee'))
        zone.eta = request.form.get("eta", "").strip()
        db.session.commit()
        flash('Zone updated', 'success')
        return redirect(url_for('admin_delivery.index'))
    return render_template('admin/delivery_zone_form.html', title='Edit Zone', zone=zone)

@bp.route('/delete/<int:zone_id>', methods=['POST'])
@login_required
def delete(zone_id):
    zone = DeliveryZone.query.get_or_404(zone_id)
    db.session.delete(zone)
    db.session.commit()
    flash('Zone deleted', 'info')
    return redirect(url_for('admin_delivery.index'))