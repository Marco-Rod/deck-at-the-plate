# backend/app/seeds/extra_tactics.py

extra_innings_tactics = [
    {
        "id": "tac_iron_closer",
        "name": "Cerrador de Hierro",
        "category": "EXTRA_INNINGS",
        "target_role": "PITCHER",
        "effects": [
            {"attribute": "control", "modifier_type": "PERCENTAGE", "value": 20},
            {"attribute": "movimiento", "modifier_type": "PERCENTAGE", "value": 15}
        ],
        "description": "Incrementa el Control (+20%) y Movimiento (+15%) para apagar el peligro en la entrada 10+."
    },
    {
        "id": "tac_walkoff_power",
        "name": "Batazo de Oro",
        "category": "EXTRA_INNINGS",
        "target_role": "BATTER",
        "effects": [
            {"attribute": "vision", "modifier_type": "PERCENTAGE", "value": 25},
            {"attribute": "poder", "modifier_type": "PERCENTAGE", "value": 20}
        ],
        "description": "Aumenta la Visión (+25%) y el Poder (+20%) para buscar dejar al rival en el campo."
    },
    {
        "id": "tac_emergency_contact",
        "name": "Contacto de Emergencia",
        "category": "EXTRA_INNINGS",
        "target_role": "BATTER",
        "effects": [
            {"attribute": "contacto", "modifier_type": "PERCENTAGE", "value": 30}
        ],
        "description": "Otorga +30% de Contacto para asegurar poner la pelota en juego y promover al corredor de 2B."
    },
    {
        "id": "tac_home_plate_lock",
        "name": "Cerrojo en Home",
        "category": "EXTRA_INNINGS",
        "target_role": "PITCHER",
        "effects": [
            {"attribute": "velocidad", "modifier_type": "PERCENTAGE", "value": 15},
            {"attribute": "control", "modifier_type": "PERCENTAGE", "value": 15}
        ],
        "description": "Neutraliza el avance del corredor automático reduciendo la probabilidad de hit con corredores en posición anotadora."
    }
]