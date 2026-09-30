"""Panel de ofertas para Mercado Libre México y WhatsApp."""

from __future__ import annotations

import base64
import json
import os
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def money(value: float) -> str:
    return f"${value:,.0f}"


def build_message(offer: dict[str, Any], link: str) -> str:
    before = f"Antes: {money(float(offer['original_price']))}\n" if offer.get("original_price") else ""
    discount = f"🔥 {offer['discount']}% de descuento\n" if offer.get("discount", 0) > 0 else ""
    return (
        "⚡ OFERTA EN MERCADO LIBRE\n\n"
        f"{offer['title']}\n\n"
        f"{discount}{before}💛 Ahora: {money(float(offer['price']))}\n"
        f"🚚 {offer['shipping']}\n\n"
        f"👉 Ver oferta: {link}\n\n"
        "Precio y disponibilidad pueden cambiar."
    )


def demo_offer(
    offer_id: str,
    title: str,
    price: float,
    original_price: float,
    discount: int,
    category: str,
    image_url: str,
    affiliate_url: str | None = None,
    status: str = "pending",
) -> dict[str, Any]:
    offer = {
        "id": offer_id,
        "external_id": f"MLM-{offer_id.upper()}",
        "title": title,
        "image_url": image_url,
        "product_url": "https://www.mercadolibre.com.mx/",
        "affiliate_url": affiliate_url,
        "price": price,
        "original_price": original_price,
        "discount": discount,
        "seller": "Tienda oficial",
        "shipping": "Envío gratis con Full",
        "category": category,
        "status": status,
        "found_at": now_iso(),
        "sent_at": now_iso() if status == "sent" else None,
    }
    offer["message"] = build_message(offer, affiliate_url or "Agrega tu enlace de afiliado")
    return offer


MEMORY_OFFERS = [
    demo_offer(
        "demo-1",
        "Audífonos inalámbricos con cancelación de ruido",
        699,
        1299,
        46,
        "Tecnología",
        "https://http2.mlstatic.com/D_NQ_NP_2X_724216-MLA79883620493_102024-F.webp",
        "https://www.mercadolibre.com.mx/",
    ),
    demo_offer(
        "demo-2",
        "Cafetera programable de 12 tazas",
        849,
        1499,
        43,
        "Hogar",
        "https://http2.mlstatic.com/D_NQ_NP_2X_759204-MLA81048750909_112024-F.webp",
    ),
    demo_offer(
        "demo-3",
        "Smartwatch deportivo resistente al agua",
        529,
        999,
        47,
        "Tecnología",
        "https://http2.mlstatic.com/D_NQ_NP_2X_914873-MLA79948913855_102024-F.webp",
        "https://www.mercadolibre.com.mx/",
        "sent",
    ),
]


def database_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def connection():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


def normalize_offer(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["price"] = float(result["price"])
    result["original_price"] = float(result["original_price"]) if result.get("original_price") else None
    for field in ("found_at", "sent_at"):
        if isinstance(result.get(field), datetime):
            result[field] = result[field].isoformat()
    return result


def list_offers() -> list[dict[str, Any]]:
    if not database_enabled():
        return MEMORY_OFFERS
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT * FROM offers ORDER BY found_at DESC")
        return [normalize_offer(row) for row in cursor.fetchall()]


def find_offer(offer_id: str) -> dict[str, Any] | None:
    return next((offer for offer in list_offers() if offer["id"] == offer_id), None)


def update_offer(offer_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    offer = find_offer(offer_id)
    if not offer:
        return None
    allowed = {"affiliate_url", "message", "status"}
    next_offer = {**offer, **{key: value for key, value in changes.items() if key in allowed}}
    if changes.get("status") == "sent":
        next_offer["sent_at"] = now_iso()

    if not database_enabled():
        index = next((i for i, item in enumerate(MEMORY_OFFERS) if item["id"] == offer_id), -1)
        if index >= 0:
            MEMORY_OFFERS[index] = next_offer
        return next_offer

    with connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE offers
            SET affiliate_url = %s, message = %s, status = %s,
                sent_at = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                next_offer.get("affiliate_url"),
                next_offer["message"],
                next_offer["status"],
                next_offer.get("sent_at"),
                offer_id,
            ),
        )
        row = cursor.fetchone()
        conn.commit()
    return normalize_offer(row) if row else None


def insert_offer(offer: dict[str, Any]) -> bool:
    if not database_enabled():
        if any(item["external_id"] == offer["external_id"] for item in MEMORY_OFFERS):
            return False
        MEMORY_OFFERS.insert(0, offer)
        return True

    with connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO offers (
                id, external_id, title, image_url, product_url, affiliate_url, price,
                original_price, discount, seller, shipping, category, status, message, found_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (external_id) DO NOTHING RETURNING id
            """,
            (
                offer["id"], offer["external_id"], offer["title"], offer["image_url"],
                offer["product_url"], offer.get("affiliate_url"), offer["price"],
                offer.get("original_price"), offer["discount"], offer["seller"],
                offer["shipping"], offer["category"], offer["status"],
                offer["message"], offer["found_at"],
            ),
        )
        inserted = cursor.fetchone() is not None
        conn.commit()
    return inserted


def requires_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected_user = os.getenv("ADMIN_USER")
        expected_password = os.getenv("ADMIN_PASSWORD")
        if not expected_user or not expected_password:
            if os.getenv("VERCEL"):
                return "Configura ADMIN_USER y ADMIN_PASSWORD en Vercel.", 503
            return view(*args, **kwargs)

        credentials = request.authorization
        valid = bool(
            credentials
            and secrets.compare_digest(credentials.username or "", expected_user)
            and secrets.compare_digest(credentials.password or "", expected_password)
        )
        if valid:
            return view(*args, **kwargs)
        return "Acceso restringido", 401, {"WWW-Authenticate": 'Basic realm="Panel de ofertas"'}

    return wrapped


@app.get("/")
@requires_admin
def home():
    return send_from_directory(ROOT / "public", "index.html")


@app.get("/assets/<path:filename>")
@requires_admin
def assets(filename: str):
    return send_from_directory(ROOT / "public", filename)


@app.get("/api/offers")
@requires_admin
def offers_api():
    return jsonify({"offers": list_offers(), "demoMode": not database_enabled()})


@app.patch("/api/offers/<offer_id>")
@requires_admin
def offer_api(offer_id: str):
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    if status is not None and status not in {"pending", "approved", "rejected", "sent"}:
        return jsonify({"error": "Estado no válido"}), 400
    affiliate_url = body.get("affiliate_url")
    if affiliate_url is not None and affiliate_url != "" and not affiliate_url.startswith("https://"):
        return jsonify({"error": "El enlace debe comenzar con https://"}), 400

    changes = {key: body[key] for key in ("affiliate_url", "message", "status") if key in body}
    offer = update_offer(offer_id, changes)
    if not offer:
        return jsonify({"error": "Oferta no encontrada"}), 404

    if body.get("prepare_share"):
        if not offer.get("affiliate_url"):
            return jsonify({"error": "Agrega el enlace oficial de afiliado antes de enviar"}), 400
        message = (body.get("message") or "").strip() or build_message(offer, offer["affiliate_url"])
        offer = update_offer(offer_id, {"message": message, "status": "sent"}) or offer
        whatsapp_url = "https://wa.me/?" + urllib.parse.urlencode({"text": message})
        return jsonify({"offer": offer, "whatsappUrl": whatsapp_url})

    return jsonify({"offer": offer})


def search_marketplace(keyword: str) -> list[dict[str, Any]]:
    token = os.getenv("MERCADOLIBRE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Falta MERCADOLIBRE_ACCESS_TOKEN")
    minimum = int(os.getenv("MIN_DISCOUNT_PERCENT", "20"))
    query = urllib.parse.urlencode({"q": keyword, "limit": 20})
    marketplace_request = urllib.request.Request(
        f"https://api.mercadolibre.com/sites/MLM/search?{query}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "OfertasAlDia/1.0"},
    )
    with urllib.request.urlopen(marketplace_request, timeout=12) as response:
        results = json.load(response).get("results", [])

    offers = []
    for item in results:
        original = item.get("original_price")
        price = item.get("price")
        discount = round((1 - price / original) * 100) if original and price and original > price else 0
        if item.get("condition") != "new" or discount < minimum:
            continue
        offer = {
            "id": str(uuid4()),
            "external_id": item["id"],
            "title": item["title"],
            "image_url": item.get("thumbnail", "").replace("-I.jpg", "-O.jpg"),
            "product_url": item["permalink"],
            "affiliate_url": None,
            "price": price,
            "original_price": original,
            "discount": discount,
            "seller": item.get("seller", {}).get("nickname", "Vendedor de Mercado Libre"),
            "shipping": "Envío gratis" if item.get("shipping", {}).get("free_shipping") else "Consulta las condiciones de envío",
            "category": item.get("category_id", "General"),
            "status": "pending",
            "found_at": now_iso(),
            "sent_at": None,
        }
        offer["message"] = build_message(offer, "Agrega tu enlace de afiliado")
        offers.append(offer)
    return offers


@app.get("/api/cron/scan")
def scan_api():
    secret = os.getenv("CRON_SECRET")
    supplied = request.headers.get("Authorization", "")
    if not secret or not secrets.compare_digest(supplied, f"Bearer {secret}"):
        return jsonify({"error": "No autorizado"}), 401

    keywords = [value.strip() for value in os.getenv("SCAN_KEYWORDS", "audifonos,smartwatch,cafetera").split(",") if value.strip()]
    inserted = 0
    errors = []
    for keyword in keywords:
        try:
            for offer in search_marketplace(keyword):
                inserted += int(insert_offer(offer))
        except Exception as error:  # Cron returns a per-keyword summary without exposing secrets.
            errors.append(f"{keyword}: {error}")
    return jsonify({"ok": not errors, "inserted": inserted, "searched": len(keywords), "errors": errors})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "3000")), debug=True)
