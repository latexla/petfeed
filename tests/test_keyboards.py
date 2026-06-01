def test_food_picker_keyboards_exist_and_carry_pet_id():
    from bot.keyboards import food_picker_filters_keyboard, food_picker_list_keyboard
    kb = food_picker_filters_keyboard(pet_id=5)
    flat = [b for row in kb.inline_keyboard for b in row]
    assert any("fp_type:dry:5" in b.callback_data for b in flat)
    assert any("fp_type:wet:5" in b.callback_data for b in flat)

    items = [{"id": 1, "brand": "Royal Canin", "name": "Sterilised 37",
              "kcal_per_100g": 350}]
    lst = food_picker_list_keyboard(items, pet_id=5, offset=0)
    flat2 = [b for row in lst.inline_keyboard for b in row]
    assert any("fp_card:1:5" in b.callback_data for b in flat2)


def test_main_menu_has_food_picker_button():
    from bot.keyboards import main_menu_keyboard
    kb = main_menu_keyboard("Барсик")
    flat = [b for row in kb.inline_keyboard for b in row]
    assert any(b.callback_data == "menu:food_picker" for b in flat)
