from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Role, Organization
from app.models.user import RoleEnum
from datetime import datetime
import json

users_bp = Blueprint('users', __name__)

def get_current_user_org():
    """Get current user and organization"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user, user.organization if user else None

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    """Get all users in the organization"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Check if user has permission to view users
    if not user.is_manager():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    # Query parameters
    role = request.args.get('role')
    is_active = request.args.get('is_active')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Build query
    query = User.query.filter_by(organization_id=org.id)
    
    if role:
        query = query.join(Role).filter(Role.name == role)
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')
    
    # Pagination
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'users': [user.to_dict() for user in users.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': users.total,
            'pages': users.pages,
            'has_next': users.has_next,
            'has_prev': users.has_prev
        }
    }), 200

@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get specific user details"""
    current_user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Users can only view their own profile unless they're managers
    if current_user.id != user_id and not current_user.is_manager():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    user = User.query.filter_by(
        id=user_id, 
        organization_id=org.id
    ).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@users_bp.route('/', methods=['POST'])
@jwt_required()
def create_user():
    """Create a new user in the organization"""
    current_user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Only managers can create users
    if not current_user.is_manager():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['email', 'username', 'password', 'first_name', 'last_name', 'role']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 409
    
    # Validate role
    try:
        role_enum = RoleEnum(data['role'])
    except ValueError:
        return jsonify({'error': 'Invalid role'}), 400
    
    # Get or create role
    role = Role.query.filter_by(name=role_enum.value).first()
    if not role:
        # Create role with basic permissions
        permissions = {
            RoleEnum.ADMIN: ['*'],
            RoleEnum.MANAGER: ['view_pipelines', 'edit_pipelines', 'view_alerts', 'manage_users'],
            RoleEnum.ANALYST: ['view_pipelines', 'view_alerts', 'view_dashboard'],
            RoleEnum.VIEWER: ['view_dashboard']
        }
        
        role = Role(
            name=role_enum.value,
            description=f'{role_enum.value.title()} role',
            permissions=permissions.get(role_enum, [])
        )
        db.session.add(role)
        db.session.flush()
    
    try:
        new_user = User(
            email=data['email'],
            username=data['username'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            organization_id=org.id,
            role_id=role.id,
            is_active=data.get('is_active', True),
            is_verified=data.get('is_verified', True)
        )
        new_user.password = data['password']
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create user', 'details': str(e)}), 500

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user"""
    current_user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Users can only update their own profile unless they're managers
    if current_user.id != user_id and not current_user.is_manager():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    user = User.query.filter_by(
        id=user_id, 
        organization_id=org.id
    ).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if data.get('first_name'):
        user.first_name = data['first_name']
    
    if data.get('last_name'):
        user.last_name = data['last_name']
    
    if data.get('username'):
        # Check if username is already taken
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Username already taken'}), 409
        user.username = data['username']
    
    # Only managers can update these fields
    if current_user.is_manager():
        if data.get('email'):
            # Check if email is already taken
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already registered'}), 409
            user.email = data['email']
        
        if data.get('role'):
            try:
                role_enum = RoleEnum(data['role'])
                role = Role.query.filter_by(name=role_enum.value).first()
                if role:
                    user.role_id = role.id
                else:
                    return jsonify({'error': 'Role not found'}), 404
            except ValueError:
                return jsonify({'error': 'Invalid role'}), 400
        
        if data.get('is_active') is not None:
            user.is_active = data['is_active']
        
        if data.get('is_verified') is not None:
            user.is_verified = data['is_verified']
    
    # Password update (users can update their own password)
    if data.get('password'):
        if current_user.id == user_id or current_user.is_manager():
            user.password = data['password']
        else:
            return jsonify({'error': 'Insufficient permissions'}), 403
    
    user.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update user', 'details': str(e)}), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete user"""
    current_user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Only managers can delete users
    if not current_user.is_manager():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    # Users cannot delete themselves
    if current_user.id == user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    user = User.query.filter_by(
        id=user_id, 
        organization_id=org.id
    ).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete user', 'details': str(e)}), 500

@users_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_roles():
    """Get available roles"""
    current_user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Only managers can view roles
    if not current_user.is_manager():
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    roles = Role.query.all()
    
    return jsonify({
        'roles': [
            {
                'name': role.name,
                'description': role.description,
                'permissions': role.permissions
            }
            for role in roles
        ]
    }), 200

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user's profile"""
    current_user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    return jsonify({
        'user': current_user.to_dict(),
        'organization': org.to_dict()
    }), 200

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user's profile"""
    current_user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data = request.get_json()
    
    # Update allowed fields
    if data.get('first_name'):
        current_user.first_name = data['first_name']
    
    if data.get('last_name'):
        current_user.last_name = data['last_name']
    
    if data.get('username'):
        # Check if username is already taken
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user and existing_user.id != current_user.id:
            return jsonify({'error': 'Username already taken'}), 409
        current_user.username = data['username']
    
    if data.get('password'):
        current_user.password = data['password']
    
    current_user.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile', 'details': str(e)}), 500 