import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import unquote
import sys
import os

def clean_text(text):
    """Metni temizle - fazla boşlukları kaldır ve noktalama kurallarını uygula"""
    # Çoklu boşlukları tek boşluğa çevir
    text = re.sub(r'\s+', ' ', text)
    # Noktalama işaretlerinden önceki boşlukları kaldır (", . ; : ! ?" gibi)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    # Kesme işaretinden önceki boşlukları kaldır (Türkçe için: "kelime 'nın" -> "kelime'nın")
    text = re.sub(r'(\w)\s+([\'\'""])', r'\1\2', text)
    
    # Virgülden sonra boşluk olmalı (yoksa ekle)
    text = re.sub(r',([^\s])', r', \1', text)
    
    # İki noktadan sonra boşluk olmalı (yoksa ekle)
    text = re.sub(r':([^\s])', r': \1', text)
    
    # Tırnak işaretinden önce boşluk olmalı (yoksa ekle, ama kelime başında değilse)
    # Önce tırnak içindeki başlangıç boşluklarını kaldır
    text = re.sub(r'"\s+', r'"', text)
    # Sonra açılış tırnağından önce boşluk ekle (kelime başında değilse)
    text = re.sub(r'([^\s])"', r'\1 "', text)
    
    # Parantez başlangıcından sonra boşluk olmamalı
    text = re.sub(r'\(\s+', r'(', text)
    
    # Parantez bitişinden önce boşluk olmamalı
    text = re.sub(r'\s+\)', r')', text)
    
    return text.strip()

def extract_markdown_content(soup):
    """Wikipedia sayfasından Markdown formatında içerik çıkar"""
    # Ana içerik div'ini bul
    content_div = soup.find('div', {'id': 'mw-content-text'})
    if not content_div:
        return None
    
    # İstenmeyen elementleri kaldır
    for element in content_div.find_all(['div', 'span'], class_=re.compile(r'reference|navbox|infobox|hatnote|mw-editsection|noprint|vertical-navbox|thumb|toc|geo|coordinates')):
        element.decompose()
    
    # Koordinat elementlerini kaldır (genellikle span.geo veya benzeri)
    for element in content_div.find_all(['span', 'div'], class_=re.compile(r'geo|coordinates|latitude|longitude')):
        element.decompose()
    
    # Script ve style taglerini kaldır
    for script in content_div(['script', 'style', 'sup', 'table']):
        script.decompose()
    
    # Markdown içeriği oluştur
    markdown_lines = []
    
    # Tüm içerik elementlerini sırayla işle
    for element in content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li']):
        tag_name = element.name
        
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Başlıkları Markdown formatına çevir
            level = int(tag_name[1])
            text = element.get_text(separator=' ', strip=True)
            # Referans numaralarını kaldır
            text = re.sub(r'\[\d+\]', '', text)
            text = clean_text(text)
            if text:
                markdown_lines.append('#' * level + ' ' + text)
                markdown_lines.append('')  # Başlıktan sonra boş satır
        
        elif tag_name == 'p':
            # Paragrafları ekle
            text = element.get_text(separator=' ', strip=True)
            # Referans numaralarını kaldır
            text = re.sub(r'\[\d+\]', '', text)
            text = clean_text(text)
            if text and len(text) > 10:  # Çok kısa paragrafları atla
                markdown_lines.append(text)
                markdown_lines.append('')  # Paragraftan sonra boş satır
        
        elif tag_name in ['ul', 'ol']:
            # Liste elemanlarını işle
            for li in element.find_all('li', recursive=False):
                text = li.get_text(separator=' ', strip=True)
                text = re.sub(r'\[\d+\]', '', text)
                text = clean_text(text)
                if text:
                    markdown_lines.append('- ' + text)
            markdown_lines.append('')  # Listeden sonra boş satır
        
        elif tag_name == 'li':
            # Tek başına liste elemanı
            text = element.get_text(separator=' ', strip=True)
            text = re.sub(r'\[\d+\]', '', text)
            text = clean_text(text)
            if text:
                markdown_lines.append('- ' + text)
    
    # Fazla boş satırları temizle (maksimum 2 boş satır)
    result = []
    prev_empty = False
    for line in markdown_lines:
        if line.strip() == '':
            if not prev_empty:
                result.append('')
                prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    
    content = '\n'.join(result).strip()
    
    # Başta koordinat satırlarını kaldır (örnek: 37°34′K 36°55′D veya 37.567°K 36.917°D)
    # Koordinat pattern: derece işareti (°) ve K/D harfleri içeren satırlar
    lines = content.split('\n')
    filtered_lines = []
    for line in lines:
        stripped_line = line.strip()
        # Koordinat satırı kontrolü: derece işareti ve K/D harfleri içeriyorsa atla
        # Ayrıca / işareti ile ayrılmış koordinatları da yakala
        if re.search(r'°.*[KD]', stripped_line) or re.search(r'[KD].*°', stripped_line) or re.search(r'\d+°.*/\s*\d+°', stripped_line):
            # Koordinat satırı, atla
            continue
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines).strip()

def scrape_wikipedia(url):
    """Wikipedia sayfasını çek ve Markdown formatında içerik çıkar"""
    print(f"Wikipedia sayfası çekiliyor: {url}")
    
    # User-Agent ekle (Wikipedia bot olarak görünmemek için)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Başlığı al
        title = soup.find('h1', class_='firstHeading')
        title_text = title.get_text(strip=True) if title else "Başlık bulunamadı"
        
        print(f"Başlık: {title_text}")
        
        # Markdown içeriği çıkar
        content = extract_markdown_content(soup)
        
        if not content:
            print("Hata: İçerik bulunamadı!")
            return None
        
        # Başlığı içeriğin başına ekle
        final_content = title_text + '\n\n' + content
        
        return final_content
        
    except requests.RequestException as e:
        print(f"Hata: Sayfa çekilemedi - {e}")
        return None
    except Exception as e:
        print(f"Hata: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python scrape_wikipedia.py <wikipedia_url>")
        print("Örnek: python scrape_wikipedia.py https://tr.wikipedia.org/wiki/İstanbul_Teknik_Üniversitesi")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # URL'den başlık çıkar (dosya adı için)
    title_slug = unquote(url.split('/')[-1])
    # Türkçe karakterleri ASCII'ye çevir ve güvenli dosya adı oluştur
    safe_title = title_slug.replace('İ', 'I').replace('ı', 'i').replace('Ş', 'S').replace('ş', 's')
    safe_title = safe_title.replace('Ğ', 'G').replace('ğ', 'g').replace('Ü', 'U').replace('ü', 'u')
    safe_title = safe_title.replace('Ö', 'O').replace('ö', 'o').replace('Ç', 'C').replace('ç', 'c')
    safe_title = re.sub(r'[^\w\s-]', '', safe_title).strip()
    safe_title = re.sub(r'[-\s]+', '_', safe_title)
    
    # Veriyi çek
    content = scrape_wikipedia(url)
    
    if content:
        # Markdown dosyası olarak kaydet
        md_filename = f"{safe_title}.md"
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nMarkdown dosyası kaydedildi: {md_filename}")
        
        print(f"\nToplam karakter sayısı: {len(content)}")
        print(f"Toplam kelime sayısı: {len(content.split())}")
        lines = [l for l in content.split('\n') if l.strip()]
        print(f"Satır sayısı: {len(lines)}")
    else:
        print("Sayfa çekilemedi!")

if __name__ == "__main__":
    main()

