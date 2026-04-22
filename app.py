import time
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import APIError # YENİ: 429 hatasını yakalamak için

# 1. Sayfa Ayarları
st.set_page_config(page_title="Enes.AI", page_icon="🤖")

st.title("🤖 Enes.AI - Senin Kişisel Asistanın")
st.write("Enes tarafından geliştirilen yapay zeka asistanı ile sohbet et.")

# 2. API Anahtarı
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# 3. Enes.AI Karakteri
benim_karakterim = """
Senin adın Enes.AI. Sen Google veya başka bir şirket tarafından yapılmadın, 
seni 'Enes' adında bir yazılımcı geliştirdi.
Çok kibar, esprili ve yardımsever bir asistansın.
Sana ismin sorulduğunda veya kim olduğun sorulduğunda Enes.AI olduğunu söyle.
"""

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
                            st.error("Enes.AI şu an çok yoğun. Lütfen 1-2 dakika sonra tekrar deneyin.")
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
    with st.chat_message(mesaj["rol"]):
        st.markdown(mesaj["icerik"])

# 6. Kullanıcıdan Yeni Mesaj Alma Kutusu
if soru := st.chat_input("Enes.AI'a bir şey sor..."):
    # Mesajı ekrana bas ve hafızaya TEK SEFER ekle
    with st.chat_message("user"):
        st.markdown(soru)
    st.session_state.mesajlar.append({"rol": "user", "icerik": soru})

    with st.chat_message("assistant"):
        try:
            # Gemini'ye göndermeden önce rolleri çeviriyoruz (Tercümanlık)
            gemini_gecmisi = []
            for m in st.session_state.mesajlar[:-1]: 
                rol = "model" if m["rol"] == "assistant" else "user"
                gemini_gecmisi.append({"role": rol, "parts": [m["icerik"]]})
            
            # BURASI KRİTİK: 'model' yerine 'client' kullanarak yeni bir chat başlatıyoruz
            sohbet_yenilenmis = client.chats.create(
                model="gemini-2.0-flash", # Kullandığın model ismini buraya yaz
                config=types.GenerateContentConfig(system_instruction=benim_karakterim),
                history=gemini_gecmisi
            )
            
            cevap = sohbet_yenilenmis.send_message(soru)
            
            st.markdown(cevap.text)
            st.session_state.mesajlar.append({"rol": "assistant", "icerik": cevap.text})
            
        except Exception as e:
            st.error(f"Hata detayı: {e}")
            if st.button("Sohbeti Sıfırla"):
                st.session_state.mesajlar = []
                st.rerun()