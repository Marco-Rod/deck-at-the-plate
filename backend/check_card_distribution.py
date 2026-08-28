#!/usr/bin/env python
"""Script para verificar la distribución de rareza de cartas en la BD"""
import os
import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import Card, CardRarity

# Configurar BD
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://game_user:game_password@localhost:5432/baseball_game")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

try:
    print("\n" + "="*80)
    print("[VERIFICACION] Distribución de rareza en BD")
    print("="*80 + "\n")
    
    # Contar por rareza
    total_cards = session.query(func.count(Card.id)).scalar()
    print(f"Total de cartas en BD: {total_cards}\n")
    
    rareza_counts = {}
    for rarity in [CardRarity.DIAMOND, CardRarity.GOLD, CardRarity.SILVER, CardRarity.BRONZE, CardRarity.COMMON]:
        count = session.query(func.count(Card.id)).filter(Card.rarity == rarity).scalar()
        rareza_counts[rarity] = count
        print(f"  {rarity.name}: {count} cartas")
    
    # Distribución de OVR
    print("\n[DISTRIBUCION_OVR]")
    ovr_stats = session.query(
        func.min(Card.overall).label('min'),
        func.max(Card.overall).label('max'),
        func.avg(Card.overall).label('avg')
    ).first()
    print(f"  Min OVR: {ovr_stats.min}")
    print(f"  Max OVR: {ovr_stats.max}")
    print(f"  Avg OVR: {ovr_stats.avg:.2f}")
    
    # Mostrar algunos ejemplos
    print("\n[EJEMPLOS_DE_CARTAS]")
    sample_cards = session.query(Card).limit(5).all()
    for card in sample_cards:
        print(f"  - {card.first_name} {card.last_name} ({card.team_id}): OVR={card.overall}, Rareza={card.rarity.name}")
    
    print("\n" + "="*80 + "\n")
    
finally:
    session.close()
