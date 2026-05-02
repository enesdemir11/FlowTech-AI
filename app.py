import time
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import os
import pandas as pd
import PyPDF2
import docx
import tempfile

# --- 1. DOSYA VE VİDEO OKUMA FONKSİYONU ---
def dosya_oku(file):
    # Görsel ise
    if file.name.endswith(('.png', '.jpg', '.jpeg')):
        return Image.open(file), "image"
    
    # Metin ise
    elif file.name.endswith('.txt'):
        return file.getvalue().decode("utf-8"), "text"
    
    # PDF ise
    elif file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()]), "text"
    
    # Excel/CSV ise
    elif file.name.endswith('.csv'):
        return pd.read_csv(file).to_string(), "text"
    elif file.name.endswith('.xlsx'):
        return pd.read_excel(file).to_string(), "text"
    
    # Word ise
    elif file.name.endswith('.docx'):
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs]), "text"
        
    # Video ise (Arka planda Google sunucularına geçici yükleme yapar)
    elif file.name.endswith(('.mp4', '.mov', '.avi')):
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as temp_video:
            temp_video.write(file.read())
            temp_path = temp_video.name

        st.toast("Video işleniyor, bu işlem dosya boyutuna göre sürebilir...", icon="⏳")
        
        # Gemini'ye yükleme
        video_file = client.files.upload(file=temp_path)

        # Video hazır olana kadar bekle
        while video_file.state.name == 'PROCESSING':
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == 'FAILED':
            st.error("Video işlenirken bir hata oluştu.")
            os.remove(temp_path)
            return None, None

        os.remove(temp_path)
        return video_file, "video"
        
    return None, None
    
    
# --- LOGO YÜKLEME ---
# Uzantı .png olarak güncellendi
logo_path = "logo.png"
if os.path.exists(logo_path):
    logo_image = Image.open(logo_path)
else:
    logo_image = "⚙️" # Görsel bulunamazsa geçici olarak çark emojisi kullan

# --- 1. SAYFA AYARLARI (Kurumsal Görünüm) ---
st.set_page_config(
    page_title="ERPnDIP", 
    page_icon=logo_image, 
    layout="centered" 
)

# --- 2. KURUMSAL TASARIM (CSS) ---
st.markdown("""
    <style>
    /* 1. Üst Boşluk (Header) Arka Planını Şeffaf Yap (Görüntü kirliliğini önler) */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important; 
    }
    
    /* 2. Kullanıcı Mesajı Kutusu (Sadece köşeleri yuvarlat, renkleri Streamlit'e bırak) */
    [data-testid="stChatMessage"]:nth-child(odd) {
        border-radius: 6px !important; 
    }

    /* 3. AI Mesajı Kutusu (Sadece ED Logosu Turuncu Vurgusunu ve yuvarlak köşeyi tut) */
    [data-testid="stChatMessage"]:nth-child(even) {
        border-left: 3px solid #E67E22 !important; 
        border-radius: 6px !important;
    }
    
    /* 4. SAĞ ÜSTTEKİ SPOR EMOJİLERİNİ (STATUS WIDGET) GİZLE */
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (YAN MENÜ) ---
with st.sidebar:
    if os.path.exists(logo_path):
        st.image(logo_image, width=180) # Logoyu menüye ekledik
    
    st.title("Sistem Kontrol Paneli")
    st.markdown("---")
    
    st.subheader("Hakkında")
    st.write("Bu sistem, endüstriyel çözümler, makine donanımları ve teknik mühendislik alanlarında danışmanlık yapmak üzere geliştirilmiştir.")
    
    st.info("Altyapı: gemini-2.5-flash") 
    
    st.markdown("---")
        
    # YENİ EKLENEN DOSYA YÜKLEME KISMI
    st.subheader("📎 Analiz İçin Medya Yükle")
    yuklenen_dosya = st.file_uploader(
        "Desteklenenler: PDF, Word, Excel, Görsel, Video", 
        type=["png", "jpg", "jpeg", "pdf", "txt", "csv", "xlsx", "docx", "mp4", "mov", "avi"]
    )
        
    st.markdown("---")
        
    # MEVCUT SIFIRLAMA BUTONU
    if st.button("🔄 Oturumu Sıfırla", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- 4. ANA EKRAN BAŞLIĞI ---
st.title("ERPnDIP AI")
st.caption("Your Industrial Solutions Partner.")
st.write("---") 

# --- 5. API ANAHTARI VE CLIENT ---
# Streamlit secrets üzerinden API anahtarını çekiyoruz
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error("API Anahtarı bulunamadı! Lütfen Streamlit secrets ayarlarını kontrol edin.")
    st.stop()

# --- 6. ENDÜSTRİYEL KARAKTER (SYSTEM PROMPT) ---
benim_karakterim = """
Adın Erper ve ERPnDIP tarafından geliştirilmiş bir yapay zekasın. Sen, makine, elektrik, teknik donanım ve endüstriyel sistemler konusunda 
uzmanlaşmış profesyonel bir 'Endüstriyel Çözüm Ortağı' yapay zekasısın.
Cevapların her zaman teknik açıdan doğru, resmi, kurumsal ve net olmalıdır. 
Kullanıcılara bir mühendislik danışmanı gibi yaklaşmalı; gereksiz uzatmalardan kaçınmalı ve çözüm odaklı olmalısın.
"""

# NOT: Buradan sonra senin mesaj döngüsü (chat loop) kodların gelmeli.


# --- YENİ 1: Üstel Geri Çekilme (Rate Limit Koruyucusu) ---
def rate_limit_korumasi(max_deneme=3, baslangic_bekleme=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            bekleme = baslangic_bekleme
            for deneme in range(max_deneme):
                try:
                    return func(*args, **kwargs)
                except APIError as e:
                    if e.code == 429: # API Limiti aşıldı hatası
                        if deneme == max_deneme - 1:
                            st.error("Erper şu an çok yoğun. Lütfen 1-2 dakika sonra tekrar deneyin.")
                            raise e
                        st.toast(f"API limiti aşıldı. {bekleme} saniye bekleniyor... (Deneme {deneme+1}/{max_deneme})")
                        time.sleep(bekleme)
                        bekleme *= 2 # Bekleme süresini katlayarak artır
                    else:
                        raise e # 429 dışındaki diğer API hatalarını doğrudan fırlat
        return wrapper
    return decorator

# --- YENİ 2: Güvenli Mesaj Gönderme Aracı ---
@rate_limit_korumasi()
def guvenli_mesaj_gonder(sohbet, mesaj):
    return sohbet.send_message(mesaj)

# --- YENİ 3: Hafıza Özetleme Sistemi (Token Tasarrufu) ---
def hafizayi_ozetle_ve_yenile():
    # Eğer mesaj sayısı 6'yı geçerse (3 soru - 3 cevap) özetleme başlar
    if len(st.session_state.mesajlar) > 6:
        st.toast("Hafıza optimize ediliyor, eski konuşmalar özetleniyor...", icon="🧠")
        
        # Geçmişi metne çevir
        gecmis_metin = "\n".join([f"{m['rol']}: {m['icerik']}" for m in st.session_state.mesajlar])
        ozet_istegi = f"Şu ana kadarki konuşmamızın kısa bir özetini çıkar, teknik veya önemli detayları koru:\n{gecmis_metin}"
        
        # Arka planda yeni bir sohbet açıp özet istiyoruz
        gecici_sohbet = client.chats.create(model="gemini-2.5-flash")
        ozet_cevap = gecici_sohbet.send_message(ozet_istegi)
        
        # Ekranda görünen mesaj listesini sıfırlayıp sadece özeti ekliyoruz
        st.session_state.mesajlar = [{"rol": "assistant", "icerik": f"*(Sistem Notu: Eski sohbet özetlendi)*\n\n{ozet_cevap.text}"}]
        
        # Modelin asıl hafızasını (history) özetle yeniliyoruz
        gecmis_icerik = [
            types.Content(role="user", parts=[types.Part.from_text("Önceki sohbetimizin özeti nedir?")]),
            types.Content(role="model", parts=[types.Part.from_text(ozet_cevap.text)])
        ]
        st.session_state.sohbet = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=benim_karakterim),
            history=gecmis_icerik
        )

# 4. Streamlit Hafızası (Session State)
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

# 5. Eski Mesajları Ekrana Çiz
for mesaj in st.session_state.mesajlar:
    # Kullanıcı için mühendis emojisi, AI için senin FT logon
    ikon = "🧑‍🔧" if mesaj["rol"] == "user" else logo_image
    
    with st.chat_message(mesaj["rol"], avatar=ikon):
        st.markdown(mesaj["icerik"])

# --- 6. ANA SOHBET DÖNGÜSÜ (Dosya Destekli) ---
if soru := st.chat_input("Erper'a bir şey sorun..."):
    
    # 1. Kullanıcı mesajını ekrana bas
    with st.chat_message("user", avatar="🧑‍🔧"):
        st.markdown(soru)
        if yuklenen_dosya:
            # Dosya varsa altında küçük bir not olarak göster
            st.caption(f"📎 Eklenen Medya: {yuklenen_dosya.name}")

    # 2. Dosya varsa okuyup soruya entegre et
    if yuklenen_dosya:
        dosya_verisi, dosya_tipi = dosya_oku(yuklenen_dosya)
        
        if dosya_tipi == "text":
            # Metin/Excel/PDF okunduysa, yapay zekaya giden sorunun sonuna gizlice ekle
            gonderilecek_mesaj = f"{soru}\n\n--- EKLENEN DOSYA İÇERİĞİ ---\n{dosya_verisi}"
            # Ekranda çok yer kaplamasın diye hafızaya sadece özetini kaydet
            hafizaya_kaydedilecek_soru = f"{soru}\n*(Kullanıcı {yuklenen_dosya.name} belgesini yükledi)*"
            
        elif dosya_tipi == "image" or dosya_tipi == "video":
            # Görsel veya video ise Gemini'nin kabul ettiği liste formatına çevir
            gonderilecek_mesaj = [soru, dosya_verisi] 
            hafizaya_kaydedilecek_soru = f"{soru}\n*(Kullanıcı bir {dosya_tipi} yükledi)*"
    else:
        # Dosya yoksa sadece soruyu gönder
        gonderilecek_mesaj = soru
        hafizaya_kaydedilecek_soru = soru

    # 3. Geçmişe kaydet (Sadece metin olarak)
    st.session_state.mesajlar.append({"rol": "user", "icerik": hafizaya_kaydedilecek_soru})

    # 4. Gemini'nin istediği geçmiş formatını (history) paketle
    gemini_gecmisi = []
    for m in st.session_state.mesajlar[:-1]: 
        rol = "model" if m["rol"] == "assistant" else "user"
        gemini_gecmisi.append({"role": rol, "parts": [{"text": m["icerik"]}]})

    sohbet_yenilenmis = client.chats.create(
        model="gemini-2.5-flash", 
        config=types.GenerateContentConfig(system_instruction=benim_karakterim),
        history=gemini_gecmisi
    )

    # 5. Yanıtı al, ekrana bas ve hafızaya kaydet (GELİŞMİŞ BEKLEME SİSTEMİ)
    with st.chat_message("assistant", avatar=logo_image):
        message_placeholder = st.empty()
        max_deneme = 4 # Deneme sayısını 4'e çıkardık
        basari = False
        import time 
        
        for deneme in range(max_deneme):
            try:
                cevap = sohbet_yenilenmis.send_message(gonderilecek_mesaj)
                basari = True
                break 
            except Exception as e:
                hata_metni = str(e)
                if "503" in hata_metni or "429" in hata_metni or "500" in hata_metni:
                    if deneme < max_deneme - 1:
                        # Katlanarak artan bekleme: 1. deneme 3 sn, 2. deneme 6 sn, 3. deneme 12 sn
                        bekleme_suresi = 3 * (2 ** deneme) 
                        st.toast(f"Google API yoğun. {bekleme_suresi} sn bekleniyor... ({deneme+1}/{max_deneme})", icon="⏳")
                        time.sleep(bekleme_suresi) 
                    else:
                        st.warning("🌐 Google sunucuları şu an isteklere kapalı. Lütfen 1-2 dakika sonra tekrar deneyin.")
                else:
                    st.error(f"Sistem Hatası: {hata_metni}")
                    break 
                    
        if basari:
            message_placeholder.markdown(cevap.text)
            st.session_state.mesajlar.append({"rol": "assistant", "icerik": cevap.text})
        else:
            if st.button("Sohbeti Sıfırla"):
                st.session_state.mesajlar = []
                st.rerun()