import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import json
import os
from datetime import datetime
import base64

# Tentative d'import de Gemini (optionnel)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Configuration de la page
st.set_page_config(page_title="Messagerie Photo", layout="centered")

# Initialisation des variables de session
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_passwords' not in st.session_state:
    st.session_state.user_passwords = ["motdepasse123"]  # Mot de passe par défaut pour l'utilisateur

# Configuration Gemini
GEMINI_API_KEY = ""
if GEMINI_AVAILABLE:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, 'secrets') else ""
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)

def verify_human_body_in_photo(image):
    """Vérifie si la photo contient une partie du corps humain avec Gemini"""
    if not GEMINI_AVAILABLE:
        st.warning("⚠️ Gemini non installé. Vérification désactivée. Installez avec: pip install google-generativeai")
        return True
    
    if not GEMINI_API_KEY:
        st.warning("⚠️ API Gemini non configurée. Vérification désactivée.")
        return True
    
    try:
        # Essayer différents modèles Gemini disponibles (versions les plus récentes d'abord)
        model_names = [
            'gemini-2.0-flash-exp',
            'gemini-exp-1206', 
            'gemini-2.0-flash',
            'gemini-1.5-flash-latest', 
            'gemini-1.5-pro-latest', 
            'gemini-1.5-flash',
            'gemini-pro-vision', 
            'gemini-pro'
        ]
        
        model = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                break
            except:
                continue
        
        if model is None:
            st.warning("⚠️ Aucun modèle Gemini disponible. Vérification désactivée.")
            return True
        
        # Conversion de l'image pour Gemini
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        prompt = """Analyse cette image et réponds UNIQUEMENT par 'OUI' ou 'NON'.
        Question: Cette image contient-elle une partie visible du corps humain (visage, tête, main, bras, jambe, pied, ou toute autre partie du corps) ?
        Réponds uniquement: OUI ou NON"""
        
        response = model.generate_content([prompt, Image.open(img_byte_arr)])
        result = response.text.strip().upper()
        
        # Note: Gemini efface automatiquement les données après traitement selon leur politique
        # Les images ne sont pas stockées de façon permanente
        
        return "OUI" in result
        
    except Exception as e:
        st.error(f"Erreur lors de la vérification: {str(e)}")
        st.info("💡 Vérification désactivée, toutes les photos sont acceptées.")
        return True

def add_text_to_image(image, text):
    """Ajoute du texte lisible sur l'image"""
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Taille de l'image
    width, height = img_copy.size
    
    # Essayer d'utiliser une police, sinon utiliser la police par défaut
    try:
        font_size = int(height * 0.06)  # 6% de la hauteur
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Calculer la position du texte (en bas de l'image)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = height - text_height - 20
    
    # Ajouter un rectangle semi-transparent pour la lisibilité
    padding = 10
    draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        fill=(0, 0, 0, 200)
    )
    
    # Ajouter le texte en blanc pour une bonne lisibilité
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    return img_copy

def get_image_download_link(img, filename):
    """Génère un lien de téléchargement pour l'image"""
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f'<a href="data:image/png;base64,{img_str}" download="{filename}" style="opacity: 0.3; font-size: 10px; color: #888;">📥</a>'

def save_message(image, text, original_image):
    """Sauvegarde un message avec l'image"""
    message = {
        'timestamp': datetime.now().isoformat(),
        'text': text,
        'image_with_text': image,
        'original_image': original_image  # Image sans texte pour téléchargement
    }
    st.session_state.messages.append(message)

def login_page():
    """Page de connexion"""
    st.title("🔐 Connexion")
    
    password = st.text_input("Entrez le code d'accès", type="password", key="login_input")
    
    if st.button("Se connecter"):
        if password == "ruffucelechien":
            st.session_state.authenticated = True
            st.session_state.is_admin = True
            st.rerun()
        elif password in st.session_state.user_passwords:
            st.session_state.authenticated = True
            st.session_state.is_admin = False
            st.rerun()
        else:
            st.error("❌ Code incorrect")

def admin_panel():
    """Panel administrateur"""
    st.sidebar.title("👑 Panel Admin")
    
    st.sidebar.subheader("Gestion des mots de passe utilisateur")
    
    # Afficher les mots de passe actuels
    st.sidebar.write("**Mots de passe actifs:**")
    for idx, pwd in enumerate(st.session_state.user_passwords):
        col1, col2 = st.sidebar.columns([3, 1])
        col1.text(pwd)
        if col2.button("🗑️", key=f"delete_{idx}"):
            st.session_state.user_passwords.pop(idx)
            st.rerun()
    
    # Ajouter un nouveau mot de passe
    new_password = st.sidebar.text_input("Nouveau mot de passe", key="new_pwd")
    if st.sidebar.button("➕ Ajouter"):
        if new_password and new_password not in st.session_state.user_passwords:
            st.session_state.user_passwords.append(new_password)
            st.sidebar.success("✅ Mot de passe ajouté")
            st.rerun()

def main_app():
    """Application principale de messagerie"""
    st.title("📸 Messagerie Photo")
    
    # Bouton de déconnexion
    if st.button("🚪 Déconnexion"):
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        st.rerun()
    
    # Panel admin si connecté en admin
    if st.session_state.is_admin:
        admin_panel()
    
    # Section d'envoi de message
    st.header("📤 Envoyer un message")
    
    # Capture photo
    camera_photo = st.camera_input("Prenez une photo")
    
    if camera_photo is not None:
        # Charger l'image
        image = Image.open(camera_photo)
        
        # Vérifier la présence d'un corps humain
        with st.spinner("🔍 Vérification de la photo..."):
            has_human = verify_human_body_in_photo(image)
        
        if not has_human:
            st.error("❌ La photo doit contenir une partie du corps humain. Veuillez reprendre la photo.")
        else:
            st.success("✅ Photo validée!")
            
            # Ajouter du texte
            text_input = st.text_input("Texte à ajouter sur la photo (optionnel)")
            
            if st.button("📨 Envoyer"):
                if text_input:
                    image_with_text = add_text_to_image(image, text_input)
                else:
                    image_with_text = image
                
                # Sauvegarder le message (image originale sans texte pour téléchargement)
                save_message(image_with_text, text_input, image)
                st.success("✅ Message envoyé!")
                st.rerun()
    
    # Affichage des messages
    st.header("💬 Messages")
    
    if st.session_state.messages:
        for idx, msg in enumerate(reversed(st.session_state.messages)):
            st.write(f"**{datetime.fromisoformat(msg['timestamp']).strftime('%d/%m/%Y %H:%M')}**")
            st.image(msg['image_with_text'], use_container_width=True)
            
            # Bouton de téléchargement discret pour l'image originale
            img_bytes = io.BytesIO()
            msg['original_image'].save(img_bytes, format='PNG')
            st.download_button(
                label="📥",
                data=img_bytes.getvalue(),
                file_name=f"photo_{len(st.session_state.messages)-idx}.png",
                mime="image/png",
                key=f"download_{idx}",
                help="Télécharger la photo originale"
            )
            st.divider()
    else:
        st.info("Aucun message pour le moment")

# Point d'entrée principal
if not st.session_state.authenticated:
    login_page()
else:
    main_app()