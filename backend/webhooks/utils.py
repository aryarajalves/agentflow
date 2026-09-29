import io
import re
import json
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

def get_value_by_path(data: Dict[str, Any], path: str) -> Any:
    """Extrai valores de dicionários aninhados usando notação de ponto (ex: 'sender.name')."""
    if not path: return None
    keys = path.split('.')
    val = data
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return None
    return val

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Transforma um dicionário aninhado em um dicionário plano com chaves compostas."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            if v and isinstance(v[0], (dict, list)):
                 items.append((new_key, json.dumps(v, ensure_ascii=False)))
            else:
                 items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)

def sanitize_table_name(name: str) -> str:
    """Garante que o nome da tabela seja seguro para o PostgreSQL."""
    clean = re.sub(r'[^a-z0-9_]', '_', name.lower().strip())
    if not clean or not clean[0].isalpha():
        clean = 'leads_' + clean
    # Limitação de tamanho do Postgres (63 caracteres)
    return clean[:63]

def normalize_phone(phone_raw: Any) -> str:
    """Remove caracteres não numéricos e lida com falhas básicas."""
    if phone_raw is None:
        return ""
    phone_str = str(phone_raw)
    phone_clean = re.sub(r'\D', '', phone_str)
    return phone_clean if phone_clean else phone_str

def get_phone_suffix(phone: str, length: int = 8) -> str:
    """Retorna os últimos N dígitos do telefone para comparação de nono dígito."""
    digits = normalize_phone(phone)
    return digits[-length:] if len(digits) >= length else digits


def texts_match_flexible(text_a: Optional[str], text_b: Optional[str]) -> bool:
    """
    Compara dois textos de templates/mensagens de forma flexível,
    desconsiderando diferenças de quebras de linha (\r\n vs \n),
    múltiplos espaços e maiúsculas/minúsculas.
    """
    if not text_a or not text_b:
        return False
    clean_a = re.sub(r'\s+', ' ', str(text_a)).strip().lower()
    clean_b = re.sub(r'\s+', ' ', str(text_b)).strip().lower()
    if not clean_a or not clean_b:
        return False
    return clean_a == clean_b or clean_a in clean_b or clean_b in clean_a


_MEDIA_TEXT_CACHE: Dict[str, str] = {}


def extract_text_from_media_url(media_url: str, filename: str = "") -> str:
    """
    Baixa e extrai automaticamente o texto de um documento (PDF, DOCX, TXT, MD, CSV)
    a partir da media_url quando o webhook não envia o campo document_content preenchido.
    """
    if not media_url or not str(media_url).startswith(("http://", "https://")):
        return ""

    if media_url in _MEDIA_TEXT_CACHE:
        return _MEDIA_TEXT_CACHE[media_url]

    url_clean = str(media_url).split("?")[0].lower()
    fname_clean = str(filename or "").lower()

    non_doc_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ogg", ".mp3", ".wav", ".m4a", ".oga", ".opus", ".mp4", ".webm")
    if url_clean.endswith(non_doc_exts) or fname_clean.endswith(non_doc_exts):
        return ""

    doc_exts = (".pdf", ".txt", ".md", ".csv", ".docx")
    is_likely_doc = (
        url_clean.endswith(doc_exts)
        or fname_clean.endswith(doc_exts)
        or "/media/proxy/" in url_clean
    )
    if not is_likely_doc:
        return ""

    try:
        import requests
        resp = requests.get(media_url, timeout=10)
        if resp.status_code != 200 or not resp.content:
            logger.warning(f"⚠️ [EXTRAÇÃO DE DOCUMENTO] Falha HTTP {resp.status_code} ao baixar mídia de '{media_url}'")
            return ""

        content_type = (resp.headers.get("content-type") or "").lower()
        raw_bytes = resp.content

        # 1. PDF
        if "pdf" in content_type or url_clean.endswith(".pdf") or fname_clean.endswith(".pdf") or raw_bytes[:4] == b"%PDF":
            extracted_pages = []
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
                for page in reader.pages:
                    page_txt = (page.extract_text() or "").strip()
                    if page_txt:
                        extracted_pages.append(page_txt)
            except Exception as pdf_err:
                logger.warning(f"⚠️ [EXTRAÇÃO PDF pypdf] Falha inicial em '{filename or media_url}': {pdf_err}")

            text_result = "\n\n".join(extracted_pages).strip()
            if not text_result:
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                        plumber_pages = [(p.extract_text() or "").strip() for p in pdf.pages]
                        text_result = "\n\n".join([p for p in plumber_pages if p]).strip()
                except Exception as plumber_err:
                    logger.warning(f"⚠️ [EXTRAÇÃO PDF pdfplumber] Falha secundária em '{filename or media_url}': {plumber_err}")

            if text_result:
                logger.info(f"📄 [EXTRAÇÃO AUTOMÁTICA DE DOCUMENTO] Texto extraído com sucesso de '{filename or media_url}' ({len(text_result)} caracteres).")
                _MEDIA_TEXT_CACHE[media_url] = text_result
            return text_result

        # 2. DOCX
        if "wordprocessingml" in content_type or url_clean.endswith(".docx") or fname_clean.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(raw_bytes))
            text_result = "\n".join([p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]).strip()
            if text_result:
                logger.info(f"📄 [EXTRAÇÃO AUTOMÁTICA DE DOCUMENTO] Texto DOCX extraído de '{filename or media_url}' ({len(text_result)} caracteres).")
                _MEDIA_TEXT_CACHE[media_url] = text_result
            return text_result

        # 3. Texto plano (TXT, MD, CSV)
        if content_type.startswith("text/") or url_clean.endswith((".txt", ".md", ".csv")) or fname_clean.endswith((".txt", ".md", ".csv")):
            text_result = resp.text.strip()
            if text_result:
                logger.info(f"📄 [EXTRAÇÃO AUTOMÁTICA DE DOCUMENTO] Texto plano extraído de '{filename or media_url}' ({len(text_result)} caracteres).")
                _MEDIA_TEXT_CACHE[media_url] = text_result
            return text_result

    except Exception as e:
        logger.warning(f"⚠️ [EXTRAÇÃO DE DOCUMENTO] Não foi possível extrair texto da URL '{media_url}': {e}")

    return ""


def extract_and_compose_media_memory(body: Dict[str, Any], base_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Extrai o conteúdo textual da mensagem/template e anexa o conteúdo integral de mídia/documento
    (document_content, filename, media_url) quando enviado no payload do webhook ou extraído via media_url.
    """
    if not isinstance(body, dict):
        return {
            "composed_message": str(base_message or ""),
            "base_message": str(base_message or ""),
            "document_content": "",
            "filename": "",
            "media_url": "",
            "template_name": "",
            "has_document_content": False,
        }

    raw_base = (
        base_message
        if base_message is not None
        else (
            get_value_by_path(body, "template_content")
            or get_value_by_path(body, "content")
            or get_value_by_path(body, "mensagem")
            or get_value_by_path(body, "text")
            or (get_value_by_path(body, "message") if isinstance(get_value_by_path(body, "message"), str) else None)
            or get_value_by_path(body, "message.template_content")
            or get_value_by_path(body, "message.content")
            or get_value_by_path(body, "message.text")
            or get_value_by_path(body, "message.mensagem")
            or ""
        )
    )
    base_msg = str(raw_base or "").strip()

    raw_doc = (
        get_value_by_path(body, "document_content")
        or get_value_by_path(body, "media_content")
        or get_value_by_path(body, "extracted_text")
        or get_value_by_path(body, "message.document_content")
        or get_value_by_path(body, "message.media_content")
        or ""
    )
    doc_content = str(raw_doc or "").strip()

    raw_filename = (
        get_value_by_path(body, "filename")
        or get_value_by_path(body, "file_name")
        or get_value_by_path(body, "message.filename")
        or get_value_by_path(body, "message.file_name")
        or ""
    )
    filename = str(raw_filename or "").strip()

    raw_media_url = (
        get_value_by_path(body, "media_url")
        or get_value_by_path(body, "file_url")
        or get_value_by_path(body, "link")
        or get_value_by_path(body, "message.media_url")
        or ""
    )
    media_url = str(raw_media_url or "").strip()

    raw_tpl_name = (
        get_value_by_path(body, "template_name")
        or get_value_by_path(body, "message.template_name")
        or ""
    )
    template_name = str(raw_tpl_name or "").strip()

    # Fallback inteligente: se document_content não veio no JSON, mas há media_url de documento (ex: PDF), extrai o texto automaticamente
    if not doc_content and media_url:
        doc_content = extract_text_from_media_url(media_url, filename)

    if doc_content:
        header = (
            f"📄 [Conteúdo da Mídia/Documento Enviado ({filename})]:"
            if filename
            else "📄 [Conteúdo da Mídia/Documento Enviado]:"
        )
        doc_section = f"{header}\n{doc_content}"
        if base_msg and doc_content not in base_msg:
            composed_message = f"{base_msg}\n\n{doc_section}"
        elif not base_msg:
            composed_message = doc_section
        else:
            composed_message = base_msg
    else:
        composed_message = base_msg

    return {
        "composed_message": composed_message,
        "base_message": base_msg,
        "document_content": doc_content,
        "filename": filename,
        "media_url": media_url,
        "template_name": template_name,
        "has_document_content": bool(doc_content),
    }


