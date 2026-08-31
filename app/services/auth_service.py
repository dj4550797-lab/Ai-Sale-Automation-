def create_admin_user(username, email, password, display_name='Admin'):
    """Create the default admin user if it doesn't exist.
    
    If the admin already exists, update its password and account details
    from the current environment configuration.
    """
    existing = User.query.filter_by(username=username).first()

    if existing:
        existing.email = email
        existing.display_name = display_name
        existing.is_active = True

        # Reset password from current ADMIN_PASSWORD environment variable.
        existing.set_password(password)

        db.session.commit()

        logger.info(f'Admin user "{username}" already exists. Password and account details updated.')
        return existing

    user = User(
        username=username,
        email=email,
        display_name=display_name,
        is_active=True,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    logger.info(f'Admin user "{username}" created.')
    return user
