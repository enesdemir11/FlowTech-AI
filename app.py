import time
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import os

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
    /* 1. Genel Ana Ekranı Koyu Temaya Zorla */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #121212 !important;
    }
    
    /* 2. Yan Menü (Sidebar) Arka Planı */
    [data-testid="stSidebar"] {
        background-color: #18181B !important; 
    }
    
    /* 3. Üst Boşluk (Header) Arka Planını Şeffaf Yap */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important; 
    }
    
    /* 4. Ekrandaki metinleri açık renge zorla */
    .stApp *, [data-testid="stSidebar"] * {
        color: #E0E0E0 !important;
    }
    
    /* 5. Kullanıcı Mesajı Kutusu */
    [data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #1E293B !important; 
        border: 1px solid #334155 !important;
        border-radius: 6px !important; 
        margin-bottom: 15px !important;
    }

    /* 6. AI Mesajı Kutusu (ED Logosu Turuncu Vurgulu) */
    [data-testid="stChatMessage"]:nth-child(even) {
        background-color: #18181B !important; 
        border-left: 3px solid #E67E22 !important; 
        border-radius: 6px !important;
        margin-bottom: 15px !important;
    }
    
    /* 7. EN ALT BÖLÜM VE MESAJ YAZMA KUTUSU (BEYAZLIK DÜZELTMESİ) */
    [data-testid="stBottomBlock"], [data-testid="stBottomBlock"] > div {
        background-color: #121212 !important; /* Alt çerçevenin dışını siyah yap */
    }
    
    [data-testid="stChatInput"] {
        background-color: #1E293B !important; /* Kutunun dış çerçevesi */
        border: 1px solid #334155 !important;
    }
    
    [data-testid="stChatInputTextArea"] {
        background-color: transparent !important; /* İç metin alanını şeffaf yapıp dış rengi almasını sağla */
        color: #E0E0E0 !important; /* Yazı rengini beyaz/gri yap */
    }

    /* 8. SAĞ ÜSTTEKİ SPOR EMOJİLERİNİ (STATUS WIDGET) GİZLE */
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

# 6. Kullanıcıdan Yeni Mesaj Alma Kutusu
if soru := st.chat_input("Erper'a bir şey sor..."):
    # 1. Kullanıcı mesajını ekrana bas ve listeye TEK SEFER ekle
    with st.chat_message("user", avatar="🧑‍🔧"):
        st.markdown(soru)
    st.session_state.mesajlar.append({"rol": "user", "icerik": soru})

    with st.chat_message("assistant", avatar=logo_image):
       # 2. Gemini'nin titiz olduğu veri formatını hazırlıyoruz (parts içindeki text yapısı)
        gemini_gecmisi = []
        for m in st.session_state.mesajlar[:-1]: # Son soru hariç geçmişi paketle
            rol = "model" if m["rol"] == "assistant" else "user"
            gemini_gecmisi.append({"role": rol, "parts": [{"text": m["icerik"]}]})
        
        # 3. Belirlediğin 2.5 modeli ile bağlantıyı kuruyoruz
        sohbet_yenilenmis = client.chats.create(
            model="gemini-2.5-flash", 
            config=types.GenerateContentConfig(system_instruction=benim_karakterim),
            history=gemini_gecmisi
        )
        
        # 4. Yanıtı al, ekrana bas ve hafızaya kaydet (YENİ TEKRAR DENEME SİSTEMİ)
        max_deneme = 3
        basari = False
        
        for deneme in range(max_deneme):
            try:
                cevap = sohbet_yenilenmis.send_message(soru)
                basari = True
                break # Başarılı olursa döngüden çık
            except Exception as e:
                hata_metni = str(e)
                # 503 (Sunucu Yoğunluğu) veya 429 (Limit Aşımı) durumunda tekrar dene
                if "503" in hata_metni or "429" in hata_metni or "500" in hata_metni:
                    if deneme < max_deneme - 1:
                        st.toast(f"Sunucu yoğun, tekrar deneniyor... ({deneme+1}/{max_deneme})")
                        time.sleep(2) 
                    else:
                        st.warning("🌐 Sunucular şu an aşırı yoğun. Lütfen 1 dakika sonra tekrar deneyin.")
                else:
                    st.error(f"Hata detayı: {hata_metni}")
                    break # Başka bir hata varsa döngüyü kır
                    
        # Eğer denemeler başarılı olduysa mesajı ekrana bas
        if basari:
            st.markdown(cevap.text)
            st.session_state.mesajlar.append({"rol": "assistant", "icerik": cevap.text})
        else:
            # Hata durumunda (başarısız olduğunda) sıfırlama butonunu göster
            if st.button("Sohbeti Sıfırla"):
                st.session_state.mesajlar = []
                st.rerun()