# strings.py
from config import CONF_NAME

S = {
    'en': {
        # ── General ──────────────────────────────────────────────────────────
        'choose_lang':          '🌐 Please choose your language:',
        'error_generic':        '❌ Something went wrong. Please try again.',
        'not_approved':         '⏳ Your registration is still under review.',
        'no_permission':        '🚫 You do not have permission to use this command.',
        'btn_back':             '⬅️ Back',
        'cancelled':            '✅ Cancelled.',

        # ── Main menu ────────────────────────────────────────────────────────
        'main_menu':            f'🏠 Welcome to {CONF_NAME}! What would you like to do?',
        'btn_housing':          '🏡 Housing',
        'btn_schedule':         '📅 Schedule',
        'btn_venue':            '📍 Venue',
        'btn_qa':               '❓ Ask a Question',
        'btn_coordinator':      '📨 Message Coordinators',

        # ── Registration ─────────────────────────────────────────────────────
        'welcome_new':          f'👋 Welcome to {CONF_NAME}!\n\nLet\'s get you registered. This will only take a minute.',
        'already_pending':      f'⏳ Your registration for {CONF_NAME} is under review. We\'ll notify you once it\'s approved!',
        'already_approved':     f'✅ You\'re already registered for {CONF_NAME}!',
        'denied_resubmit':      '❌ Your registration was denied.\n\n*Reason:* {reason}\n\nYou may upload a new payment receipt to reapply.',
        'enter_name':           '📝 Please enter your *full name* (first and last):',
        'invalid_name':         '❌ Please enter both your first and last name.',
        'enter_age':            '🔢 Please enter your *age*:',
        'invalid_age':          '❌ Please enter a valid age (digits only, max 2).',
        'choose_gender':        '👤 Please select your gender:',
        'btn_male':             '♂️ Male',
        'btn_female':           '♀️ Female',
        'share_phone':          '📱 Please share your phone number:',
        'btn_share_phone':      '📲 Share Phone Number',
        'payment_instructions': (
            f'💳 *Payment*\n\n'
            f'Please complete your registration payment at the link below:\n\n'
            f'{{payment_link}}\n\n'
            f'Once you\'ve paid, come back and send your *payment receipt* (photo or screenshot).'
        ),
        'upload_receipt':       '📎 Please upload your *payment receipt* (photo or screenshot):',
        'receipt_submitted':    (
            '✅ Your payment confirmation has been received!\n\n'
            'Our team will review it and notify you once your registration is approved.'
        ),
        'approved_welcome':     (
            f'🎉 *You\'re registered for {CONF_NAME}!*\n\n'
            'Your registration has been approved. Use the menu below to access all features.'
        ),
        'denied_notification':  '❌ *Registration Update*\n\nYour registration was not approved.\n\n*Reason:* {reason}\n\nPlease contact the organizers if you have questions.',

        # ── Housing ──────────────────────────────────────────────────────────
        'housing_paused':       '⏸ Housing reservations are not available right now.',
        'housing_prompt':       '🏡 Do you need local housing for the conference?',
        'btn_housing_yes':      '✅ Yes, I need housing',
        'btn_housing_no':       '❌ No, I have my own',
        'no_housing_needed':    '👍 Got it! You\'re all set without housing.',
        'no_houses_available':  '😔 No housing is available for your group right now. Please contact the organizers.',
        'housing_list_header':  '🏠 Available houses — tap one to reserve:',
        'house_full_label':     '{name} — FULL',
        'house_spots_label':    '{name} — {taken}/{capacity} spots taken',
        'house_full_msg':       '😔 That house is full. Please choose another.',
        'house_confirm':        '🏡 Reserve a spot at *{name}*?',
        'btn_confirm_yes':      '✅ Yes, reserve',
        'btn_confirm_no':       '❌ Cancel',
        'house_reserved':       '✅ You\'re reserved at *{name}*!',
        'current_reservation':  '🏡 Your current reservation: *{name}*\n\nWould you like to cancel it?',
        'btn_cancel_reservation': '❌ Cancel Reservation',
        'reservation_cancelled': '✅ Your reservation has been cancelled. You can reserve a new spot anytime.',

        # ── Schedule ─────────────────────────────────────────────────────────
        'no_schedule':          '📅 The schedule hasn\'t been posted yet. Check back soon!',

        # ── Venue ────────────────────────────────────────────────────────────
        'no_venue':             '📍 Venue information hasn\'t been posted yet. Check back soon!',

        # ── Q&A ──────────────────────────────────────────────────────────────
        'qa_paused':            '⏸ Q&A submissions are paused right now.',
        'qa_prompt':            '❓ Type your question for the speakers:',
        'qa_submitted':         '✅ Your question has been submitted!',
        'qa_rate_limited':      '❌ You\'ve reached the question limit ({limit} questions max).',

        # ── Coordinator messages ──────────────────────────────────────────────
        'messages_paused':      '⏸ Coordinator messaging is paused right now.',
        'coordinator_prompt':   '📨 Type your message to the coordinators:',
        'coordinator_submitted':'✅ Your message has been sent to the coordinators!',

        # ── Admin ─────────────────────────────────────────────────────────────
        'admin_no_pending':     '✅ No registrations pending review.',
        'admin_pending_header': '📋 *Pending registrations ({count}):*\n\n',
        'admin_pending_entry':  '👤 *{name}* | {age}y | {gender} | @{username}\n',
        'admin_approved':       '✅ {name} has been approved and notified.',
        'admin_denied':         '❌ {name} has been denied and notified.',
        'admin_deny_prompt':    'Enter the reason for denial (will be sent to the user):',
        'admin_no_participants':'No participants found.',
        'admin_broadcast_sent': '📢 Broadcast sent to {count} approved participants.',
        'admin_house_added':    '✅ House *{name}* added ({gender}, capacity {capacity}).',
        'admin_house_exists':   '❌ A house named *{name}* already exists.',
        'admin_house_removed':  '✅ House *{name}* removed.',
        'admin_house_not_found':'❌ No house found with name *{name}*.',
        'admin_house_occupied': '⚠️ House *{name}* has {count} reservation(s). Remove anyway? Reply /confirmremove {name}',
        'admin_houses_list':    '🏠 *Houses:*\n\n{list}',
        'admin_resident_moved': '✅ {user} moved to *{house}*.',
        'admin_user_not_found': '❌ No user found with that ID.',
        'admin_feature_paused': '⏸ Feature *{feature}* paused.',
        'admin_feature_resumed':'▶️ Feature *{feature}* resumed.',
        'admin_schedule_set':   '✅ Schedule updated.',
        'admin_venue_set':      '✅ Venue info updated.',
        'admin_added':          '✅ Admin {chat_id} added.',
        'admin_user_removed':   '✅ User removed.',
        'admin_nuke_confirm1':  '⚠️ This will delete ALL participant data. Type /nuke2 to confirm.',
        'admin_nuke_confirm2':  '🔴 FINAL WARNING: all data will be wiped. Type /nuke3 to proceed.',
        'admin_nuked':          '💥 All participant data has been deleted.',
        'admin_set_prompt':     'Send the new {field} text now:',
        'admin_status':         (
            '📊 *Bot Status*\n\n'
            '👥 Total participants: {total}\n'
            '✅ Approved: {approved}\n'
            '⏳ Pending review: {pending}\n'
            '❌ Denied: {denied}\n'
            '🏠 Housing reserved: {housed}'
        ),
    },

    'uk': {
        # ── General ──────────────────────────────────────────────────────────
        'choose_lang':          '🌐 Будь ласка, оберіть мову:',
        'error_generic':        '❌ Щось пішло не так. Будь ласка, спробуйте ще раз.',
        'not_approved':         '⏳ Ваша реєстрація ще на розгляді.',
        'no_permission':        '🚫 У вас немає дозволу використовувати цю команду.',
        'btn_back':             '⬅️ Назад',
        'cancelled':            '✅ Скасовано.',

        # ── Main menu ────────────────────────────────────────────────────────
        'main_menu':            f'🏠 Ласкаво просимо до {CONF_NAME}! Що бажаєте зробити?',
        'btn_housing':          '🏡 Житло',
        'btn_schedule':         '📅 Розклад',
        'btn_venue':            '📍 Місце проведення',
        'btn_qa':               '❓ Запитати доповідача',
        'btn_coordinator':      '📨 Написати координаторам',

        # ── Registration ─────────────────────────────────────────────────────
        'welcome_new':          f'👋 Ласкаво просимо до {CONF_NAME}!\n\nДавайте зареєструємо вас. Це займе лише хвилину.',
        'already_pending':      f'⏳ Ваша реєстрація на {CONF_NAME} на розгляді. Ми повідомимо вас, коли її схвалять!',
        'already_approved':     f'✅ Ви вже зареєстровані на {CONF_NAME}!',
        'denied_resubmit':      '❌ Вашу реєстрацію було відхилено.\n\n*Причина:* {reason}\n\nВи можете завантажити новий чек для повторної подачі.',
        'enter_name':           "📝 Будь ласка, введіть ваше *повне ім'я* (ім'я та прізвище):",
        'invalid_name':         "❌ Будь ласка, введіть ім'я та прізвище.",
        'enter_age':            '🔢 Будь ласка, введіть ваш *вік*:',
        'invalid_age':          '❌ Будь ласка, введіть коректний вік (лише цифри, максимум 2).',
        'choose_gender':        '👤 Будь ласка, оберіть вашу стать:',
        'btn_male':             '♂️ Чоловік',
        'btn_female':           '♀️ Жінка',
        'share_phone':          '📱 Будь ласка, поділіться своїм номером телефону:',
        'btn_share_phone':      '📲 Поділитися номером телефону',
        'payment_instructions': (
            f'💳 *Оплата*\n\n'
            f'Будь ласка, здійсніть оплату реєстраційного внеску за посиланням нижче:\n\n'
            f'{{payment_link}}\n\n'
            f'Після оплати поверніться сюди та надішліть *квитанцію про оплату* (фото або скриншот).'
        ),
        'upload_receipt':       '📎 Будь ласка, завантажте *квитанцію про оплату* (фото або скриншот):',
        'receipt_submitted':    (
            '✅ Ваше підтвердження оплати отримано!\n\n'
            'Наша команда перевірить його та повідомить вас після схвалення реєстрації.'
        ),
        'approved_welcome':     (
            f'🎉 *Вітаємо! Ви зареєстровані на {CONF_NAME}!*\n\n'
            'Вашу реєстрацію схвалено. Використовуйте меню нижче для доступу до всіх функцій.'
        ),
        'denied_notification':  '❌ *Оновлення реєстрації*\n\nВашу реєстрацію не схвалено.\n\n*Причина:* {reason}\n\nЗверніться до організаторів, якщо у вас є запитання.',

        # ── Housing ──────────────────────────────────────────────────────────
        'housing_paused':       '⏸ Бронювання житла наразі недоступне.',
        'housing_prompt':       '🏡 Чи потребуєте ви проживання під час конференції?',
        'btn_housing_yes':      '✅ Так, потребую',
        'btn_housing_no':       '❌ Ні, маю своє',
        'no_housing_needed':    '👍 Зрозуміло! Все влаштовано без проживання.',
        'no_houses_available':  '😔 На жаль, проживання для вашої групи наразі недоступне. Зверніться до організаторів.',
        'housing_list_header':  '🏠 Доступне житло — натисніть, щоб забронювати:',
        'house_full_label':     '{name} — ЗАЙНЯТИЙ',
        'house_spots_label':    '{name} — {taken}/{capacity} місць зайнято',
        'house_full_msg':       '😔 Цей будинок заповнений. Будь ласка, оберіть інший.',
        'house_confirm':        '🏡 Забронювати місце в *{name}*?',
        'btn_confirm_yes':      '✅ Так, бронюю',
        'btn_confirm_no':       '❌ Скасувати',
        'house_reserved':       '✅ Ви заброньовані в *{name}*!',
        'current_reservation':  '🏡 Ваше поточне бронювання: *{name}*\n\nБажаєте скасувати?',
        'btn_cancel_reservation': '❌ Скасувати бронювання',
        'reservation_cancelled': '✅ Ваше бронювання скасовано. Ви можете забронювати нове місце будь-коли.',

        # ── Schedule ─────────────────────────────────────────────────────────
        'no_schedule':          '📅 Розклад ще не опубліковано. Перевірте пізніше!',

        # ── Venue ────────────────────────────────────────────────────────────
        'no_venue':             '📍 Інформація про місце проведення ще не опублікована. Перевірте пізніше!',

        # ── Q&A ──────────────────────────────────────────────────────────────
        'qa_paused':            '⏸ Прийом запитань наразі призупинено.',
        'qa_prompt':            '❓ Введіть ваше запитання для доповідачів:',
        'qa_submitted':         '✅ Ваше запитання надіслано!',
        'qa_rate_limited':      '❌ Ви досягли ліміту запитань (максимум {limit}).',

        # ── Coordinator messages ──────────────────────────────────────────────
        'messages_paused':      '⏸ Зв\'язок з координаторами наразі призупинено.',
        'coordinator_prompt':   '📨 Введіть повідомлення для координаторів:',
        'coordinator_submitted':'✅ Ваше повідомлення надіслано координаторам!',

        # ── Admin ─────────────────────────────────────────────────────────────
        'admin_no_pending':     '✅ Немає реєстрацій на розгляді.',
        'admin_pending_header': '📋 *Очікують розгляду ({count}):*\n\n',
        'admin_pending_entry':  '👤 *{name}* | {age}р | {gender} | @{username}\n',
        'admin_approved':       '✅ {name} схвалено та повідомлено.',
        'admin_denied':         '❌ {name} відхилено та повідомлено.',
        'admin_deny_prompt':    'Введіть причину відхилення (буде надіслана користувачу):',
        'admin_no_participants':'Учасників не знайдено.',
        'admin_broadcast_sent': '📢 Повідомлення надіслано {count} схваленим учасникам.',
        'admin_house_added':    '✅ Будинок *{name}* додано ({gender}, місткість {capacity}).',
        'admin_house_exists':   '❌ Будинок з назвою *{name}* вже існує.',
        'admin_house_removed':  '✅ Будинок *{name}* видалено.',
        'admin_house_not_found':'❌ Будинок з назвою *{name}* не знайдено.',
        'admin_house_occupied': '⚠️ У будинку *{name}* є {count} бронювань. Видалити? Відповідь /confirmremove {name}',
        'admin_houses_list':    '🏠 *Будинки:*\n\n{list}',
        'admin_resident_moved': '✅ {user} переміщено до *{house}*.',
        'admin_user_not_found': '❌ Користувача з таким ID не знайдено.',
        'admin_feature_paused': '⏸ Функцію *{feature}* призупинено.',
        'admin_feature_resumed':'▶️ Функцію *{feature}* відновлено.',
        'admin_schedule_set':   '✅ Розклад оновлено.',
        'admin_venue_set':      '✅ Інформацію про місце оновлено.',
        'admin_added':          '✅ Адміністратора {chat_id} додано.',
        'admin_user_removed':   '✅ Користувача видалено.',
        'admin_nuke_confirm1':  '⚠️ Це видалить УСІ дані учасників. Введіть /nuke2 для підтвердження.',
        'admin_nuke_confirm2':  '🔴 ОСТАТОЧНЕ ПОПЕРЕДЖЕННЯ: всі дані будуть видалені. Введіть /nuke3 для продовження.',
        'admin_nuked':          '💥 Усі дані учасників видалено.',
        'admin_set_prompt':     'Надішліть новий текст для {field}:',
        'admin_status':         (
            '📊 *Статус бота*\n\n'
            '👥 Всього учасників: {total}\n'
            '✅ Схвалено: {approved}\n'
            '⏳ На розгляді: {pending}\n'
            '❌ Відхилено: {denied}\n'
            '🏠 Забронювали житло: {housed}'
        ),
    }
}


def t(lang: str, key: str, **kwargs) -> str:
    """Get a translated string. Falls back to 'en' if lang not found."""
    text = S.get(lang, S['en']).get(key, S['en'].get(key, f'[{key}]'))
    return text.format(**kwargs) if kwargs else text
