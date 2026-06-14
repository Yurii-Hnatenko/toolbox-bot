@router.callback_query(F.data == "skip_photo")
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    results = data.get("results", [])
    toolbox_id = data["toolbox_id"]
    
    async with async_session() as session:
        user = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user.scalar_one()
        
        all_present = True
        for res in results:
            check = ToolCheck(
                toolbox_id=toolbox_id,
                user_id=user.id,
                tool_name=res["tool"],
                is_present=res["present"],
                comment=res.get("comment", ""),
                photo_path=None
            )
            session.add(check)
            if not res["present"]:
                all_present = False
        
        result = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id))
        box_status = result.scalar_one_or_none()
        if not box_status:
            box_status = BoxStatus(toolbox_id=toolbox_id)
            session.add(box_status)
        
        box_status.last_check_time = datetime.utcnow()
        box_status.last_check_user = user.id
        box_status.is_complete = all_present
        
        await session.commit()
    
    total = len(results)
    present_count = sum(1 for r in results if r["present"])
    result_text = f"✅ Перевірку завершено!\n\n✅ Є: {present_count}/{total}\n❌ Відсутні: {total - present_count}/{total}"
    
    await callback.message.answer(
        result_text,
        reply_markup=main_menu_by_role(active_role.get(callback.from_user.id, "operator"))
    )
    await state.clear()
    await callback.answer()

@router.message(CheckState.photo)
async def save_photo_and_check(message: Message, state: FSMContext):
    photo_path = None
    if message.photo:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        os.makedirs("media", exist_ok=True)
        photo_path = f"media/{file.file_id}.jpg"
        await message.bot.download_file(file.file_path, photo_path)
    
    data = await state.get_data()
    results = data.get("results", [])
    toolbox_id = data["toolbox_id"]
    
    async with async_session() as session:
        user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user.scalar_one()
        
        all_present = True
        for res in results:
            check = ToolCheck(
                toolbox_id=toolbox_id,
                user_id=user.id,
                tool_name=res["tool"],
                is_present=res["present"],
                comment=res.get("comment", ""),
                photo_path=photo_path
            )
            session.add(check)
            if not res["present"]:
                all_present = False
        
        result = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id))
        box_status = result.scalar_one_or_none()
        if not box_status:
            box_status = BoxStatus(toolbox_id=toolbox_id)
            session.add(box_status)
        
        box_status.last_check_time = datetime.utcnow()
        box_status.last_check_user = user.id
        box_status.is_complete = all_present
        
        await session.commit()
    
    total = len(results)
    present_count = sum(1 for r in results if r["present"])
    result_text = f"✅ Перевірку завершено!\n\n✅ Є: {present_count}/{total}\n❌ Відсутні: {total - present_count}/{total}"
    
    await message.answer(
        result_text,
        reply_markup=main_menu_by_role(active_role.get(message.from_user.id, "operator"))
    )
    await state.clear()
