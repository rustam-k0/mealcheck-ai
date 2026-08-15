RECOGNITION_SYSTEM_PROMPT = """Определи все видимые или названные продукты и их наиболее вероятные порции. Один продукт — один item; название пиши на языке пользователя. Учитывай видимые соусы, масло и напитки, но не выдумывай скрытые ингредиенты. Не считай КБЖУ, не задавай вопросов. Верни только JSON по схеме."""

CALCULATION_SYSTEM_PROMPT = """Рассчитай примерные ккал, белки, жиры и углеводы подтверждённого приёма пищи. Верни по одному item на каждую входную позицию, ничего не добавляй и не пропускай. total — сумма items. Верни только JSON по схеме."""

RECOGNITION_SCHEMA = '{"items":[{"name":"string","amount":0,"unit":"g|ml|piece|portion","preparation":"string|null","visible_evidence":"string|null","confidence":0.0}]}'
NUTRITION_SCHEMA = '{"items":[{"name":"string","confirmed_amount_g":0,"kcal":0,"protein_g":0,"fat_g":0,"carbs_g":0,"confidence":0.0}],"total":{"kcal":0,"protein_g":0,"fat_g":0,"carbs_g":0},"estimated_error_percent":0,"uncertainty_reasons":["string"]}'
