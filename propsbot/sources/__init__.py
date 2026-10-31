"""Datakällor. Lägg till en adapter per odds-API / händelsedata-API.

En odds-adapter ska returnera list[OddsQuote] med book, player_id, market
("shots", "shots_on_target", "goal", "assist"), line, side ("over"/"under"),
odds och ts. Matcha spelarnamn mot era player_id i adaptern.
"""
