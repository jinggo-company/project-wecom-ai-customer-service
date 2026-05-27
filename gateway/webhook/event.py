"""WeCom Event Callback Handler (成员变更/群事件等)"""

import logging

logger = logging.getLogger(__name__)


def handle_event_message(msg_data):
    """
    Handle WeCom event callbacks.
    
    Supported events:
    - change_contact: member/department change
    - change_external_contact: external contact change
    - change_external_chat: group chat change
    
    Args:
        msg_data: raw event dict from WeCom callback
    
    Returns:
        dict: processing result
    """
    event = msg_data.get("Event", "")
    change_type = msg_data.get("ChangeType", "")

    event_handlers = {
        "change_contact": handle_contact_change,
        "change_external_contact": handle_external_contact_change,
        "change_external_chat": handle_external_chat_change,
    }

    handler = event_handlers.get(event)
    if handler:
        return handler(msg_data, change_type)
    
    logger.info("Unhandled event: Event=%s, ChangeType=%s", event, change_type)
    return {"status": "unhandled_event", "event": event, "change_type": change_type}


def handle_contact_change(msg_data, change_type):
    """Handle member/department change events."""
    handlers = {
        "create_user": handle_create_user,
        "update_user": handle_update_user,
        "delete_user": handle_delete_user,
        "create_party": handle_create_party,
        "update_party": handle_update_party,
        "delete_party": handle_delete_party,
    }
    handler = handlers.get(change_type)
    if handler:
        return handler(msg_data)
    logger.info("Unhandled contact change: %s", change_type)
    return {"status": "unhandled", "change_type": change_type}


def handle_create_user(msg_data):
    """Handle new member creation."""
    userid = msg_data.get("UserID", "")
    logger.info("New member created: userid=%s", userid)
    return {
        "status": "processed",
        "action": "create_user",
        "userid": userid,
        "name": msg_data.get("Name", ""),
    }


def handle_update_user(msg_data):
    """Handle member update."""
    userid = msg_data.get("UserID", "")
    logger.info("Member updated: userid=%s", userid)
    return {"status": "processed", "action": "update_user", "userid": userid}


def handle_delete_user(msg_data):
    """Handle member deletion."""
    userid = msg_data.get("UserID", "")
    logger.info("Member deleted: userid=%s", userid)
    return {"status": "processed", "action": "delete_user", "userid": userid}


def handle_create_party(msg_data):
    """Handle department creation."""
    party_id = msg_data.get("Id", "")
    logger.info("Department created: id=%s", party_id)
    return {"status": "processed", "action": "create_party", "party_id": party_id}


def handle_update_party(msg_data):
    """Handle department update."""
    party_id = msg_data.get("Id", "")
    logger.info("Department updated: id=%s", party_id)
    return {"status": "processed", "action": "update_party", "party_id": party_id}


def handle_delete_party(msg_data):
    """Handle department deletion."""
    party_id = msg_data.get("Id", "")
    logger.info("Department deleted: id=%s", party_id)
    return {"status": "processed", "action": "delete_party", "party_id": party_id}


def handle_external_contact_change(msg_data, change_type):
    """Handle external contact (客户) change events."""
    handlers = {
        "add_external_contact": handle_add_external_contact,
        "edit_external_contact": handle_edit_external_contact,
        "del_external_contact": handle_del_external_contact,
        "del_follow_user": handle_del_follow_user,
    }
    handler = handlers.get(change_type)
    if handler:
        return handler(msg_data)
    logger.info("Unhandled external contact change: %s", change_type)
    return {"status": "unhandled", "change_type": change_type}


def handle_add_external_contact(msg_data):
    """Handle new external contact added — triggers welcome SOP."""
    userid = msg_data.get("UserID", "")
    external_userid = msg_data.get("ExternalUserID", "")
    state = msg_data.get("State", "")  # channel tracking state
    welcome_code = msg_data.get("WelcomeCode", "")

    logger.info(
        "External contact added: staff=%s, customer=%s, state=%s",
        userid, external_userid, state,
    )
    return {
        "status": "processed",
        "action": "add_external_contact",
        "staff_userid": userid,
        "external_userid": external_userid,
        "state": state,
        "welcome_code": welcome_code,
        "trigger_sop": "welcome",  # Signal to SOP engine
    }


def handle_edit_external_contact(msg_data):
    """Handle external contact info change (e.g., tag update)."""
    userid = msg_data.get("UserID", "")
    external_userid = msg_data.get("ExternalUserID", "")
    logger.info("External contact edited: staff=%s, customer=%s", userid, external_userid)
    return {
        "status": "processed",
        "action": "edit_external_contact",
        "staff_userid": userid,
        "external_userid": external_userid,
    }


def handle_del_external_contact(msg_data):
    """Handle external contact deleted."""
    userid = msg_data.get("UserID", "")
    external_userid = msg_data.get("ExternalUserID", "")
    logger.info("External contact deleted: staff=%s, customer=%s", userid, external_userid)
    return {
        "status": "processed",
        "action": "del_external_contact",
        "staff_userid": userid,
        "external_userid": external_userid,
    }


def handle_del_follow_user(msg_data):
    """Handle staff deleted by external contact (被删除/拉黑)."""
    userid = msg_data.get("UserID", "")
    external_userid = msg_data.get("ExternalUserID", "")
    logger.info(
        "External contact removed staff: staff=%s, customer=%s",
        userid, external_userid,
    )
    return {
        "status": "processed",
        "action": "del_follow_user",
        "staff_userid": userid,
        "external_userid": external_userid,
    }


def handle_external_chat_change(msg_data, change_type):
    """Handle group chat change events."""
    handlers = {
        "create": handle_chat_create,
        "update": handle_chat_update,
        "dismiss": handle_chat_dismiss,
    }
    handler = handlers.get(change_type)
    if handler:
        return handler(msg_data)
    logger.info("Unhandled external chat change: %s", change_type)
    return {"status": "unhandled", "change_type": change_type}


def handle_chat_create(msg_data):
    """Handle new group chat created."""
    chat_id = msg_data.get("ChatId", "")
    logger.info("Group chat created: chat_id=%s", chat_id)
    return {"status": "processed", "action": "chat_create", "chat_id": chat_id}


def handle_chat_update(msg_data):
    """Handle group chat updated (member change, etc)."""
    chat_id = msg_data.get("ChatId", "")
    logger.info("Group chat updated: chat_id=%s", chat_id)
    return {"status": "processed", "action": "chat_update", "chat_id": chat_id}


def handle_chat_dismiss(msg_data):
    """Handle group chat dismissed."""
    chat_id = msg_data.get("ChatId", "")
    logger.info("Group chat dismissed: chat_id=%s", chat_id)
    return {"status": "processed", "action": "chat_dismiss", "chat_id": chat_id}
