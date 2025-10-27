import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def generate_verification_token():
    """Генерирует уникальный токен для верификации email"""
    return str(uuid.uuid4())


def send_verification_email(user_profile):
    """
    Отправляет подтверждающее письмо пользователю
    """
    try:
        # Проверяем настройки email
        from django.conf import settings
        if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
            print("❌ EMAIL_HOST_USER not configured")
            return False
        
        # Проверяем, не используется ли console backend (для отладки)
        if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
            print("ℹ️ Using console email backend - email will be printed to console")
        
        # Генерируем токен верификации
        verification_token = generate_verification_token()
        user_profile.email_verification_token = verification_token
        user_profile.save()
        
        # Формируем ссылку для подтверждения
        # Базовый URL берём из настроек (по умолчанию основной сайт)
        base_url = getattr(settings, 'VERIFICATION_BASE_URL', 'https://valor-games.co').rstrip('/')
        verification_url = f"{base_url}/verify-email/{verification_token}/"
        
        # Тема письма
        subject = 'Confirmación de registro - Valor Games'
        
        # HTML содержимое письма
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Confirmación de registro</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .button {{ 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #4CAF50; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 20px 0;
                }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Bienvenido a Valor Games!</h1>
                </div>
                <div class="content">
                    <h2>¡Hola!</h2>
                    <p>Gracias por registrarte en nuestra plataforma. Para completar tu registro, por favor confirma tu dirección de email.</p>
                    
                    <p><strong>Tus datos:</strong></p>
                    <ul>
                        <li>Email: {user_profile.email}</li>
                        <li>ID de usuario: {user_profile.user_id}</li>
                        <li>País: {user_profile.country or 'No especificado'}</li>
                    </ul>
                    
                    <p>Haz clic en el botón de abajo para confirmar tu email:</p>
                    
                    <a href="{verification_url}" class="button">Confirmar Email</a>
                    
                    <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                    <p><a href="{verification_url}">{verification_url}</a></p>
                    
                    <p><strong>Importante:</strong> Este enlace es válido por 24 horas.</p>
                </div>
                <div class="footer">
                    <p>Saludos cordiales,<br>Equipo Valor Games</p>
                    <p>Si no te registraste en nuestro sitio, simplemente ignora este correo.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия письма
        plain_message = f"""
        ¡Bienvenido a Valor Games!
        
        ¡Hola!
        
        Gracias por registrarte en nuestra plataforma. Para completar tu registro, por favor confirma tu dirección de email.
        
        Tus datos:
        - Email: {user_profile.email}
        - ID de usuario: {user_profile.user_id}
        - País: {user_profile.country or 'No especificado'}
        
        Para confirmar tu email, visita este enlace:
        {verification_url}
        
        Importante: Este enlace es válido por 24 horas.
        
        Saludos cordiales,
        Equipo Valor Games
        
        Si no te registraste en nuestro sitio, simplemente ignora este correo.
        """
        
        # Отправляем письмо
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_profile.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Verification email sent to {user_profile.email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending verification email to {user_profile.email}: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_welcome_email(user_profile):
    """
    Отправляет приветственное письмо после подтверждения email
    """
    try:
        subject = 'Email confirmado - ¡Bienvenido a Valor Games!'
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Email confirmado</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 ¡Email confirmado exitosamente!</h1>
                </div>
                <div class="content">
                    <h2>¡Felicitaciones!</h2>
                    <p>Tu dirección de email <strong>{user_profile.email}</strong> ha sido confirmada exitosamente.</p>
                    
                    <p>Ahora puedes disfrutar de todas las funcionalidades de la plataforma Valor Games:</p>
                    <ul>
                        <li>Recargar saldo</li>
                        <li>Retirar fondos</li>
                        <li>Recibir notificaciones</li>
                        <li>Participar en promociones</li>
                    </ul>
                    
                    <p>Tu ID de usuario: <strong>{user_profile.user_id}</strong></p>
                    
                    <p>¡Que tengas buena suerte jugando!</p>
                </div>
                <div class="footer">
                    <p>Saludos cordiales,<br>Equipo Valor Games</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = f"""
        ¡Email confirmado exitosamente!
        
        ¡Felicitaciones!
        
        Tu dirección de email {user_profile.email} ha sido confirmada exitosamente.
        
        Ahora puedes disfrutar de todas las funcionalidades de la plataforma Valor Games:
        - Recargar saldo
        - Retirar fondos
        - Recibir notificaciones
        - Participar en promociones
        
        Tu ID de usuario: {user_profile.user_id}
        
        ¡Que tengas buena suerte jugando!
        
        Saludos cordiales,
        Equipo Valor Games
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_profile.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Welcome email sent to {user_profile.email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending welcome email to {user_profile.email}: {e}")
        return False