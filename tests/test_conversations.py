"""
Flixora AI Sales Automation Agent — Client Conversations Tests
"""
import pytest
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import Lead, Conversation, Message, KnowledgeBase, PricingPlan, Setting
from app.constants import ConversationStatus
from app.services.auth_service import create_admin_user
from app.services.conversation_service import (
    create_or_get_conversation, add_message, generate_chatbot_reply, toggle_takeover_status
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


def test_create_or_get_conversation(app):
    """Test creating conversation session initializes status maps."""
    with app.app_context():
        lead = Lead(business_name="Nail Boutique", business_category="salon")
        db.session.add(lead)
        db.session.commit()

        conv = create_or_get_conversation(lead.id, 'whatsapp')
        assert conv is not None
        assert conv.status == ConversationStatus.AI_ACTIVE
        assert conv.channel == 'whatsapp'

        # Get existing
        conv2 = create_or_get_conversation(lead.id, 'email')
        assert conv2.id == conv.id
        assert conv2.channel == 'whatsapp'  # maintains original channel


def test_add_message(app):
    """Test appending message updates session counters."""
    with app.app_context():
        lead = Lead(business_name="Nail Boutique", business_category="salon")
        db.session.add(lead)
        db.session.commit()

        conv = create_or_get_conversation(lead.id, 'whatsapp')
        msg = add_message(conv.id, 'client', "Hello assistant")
        assert msg is not None
        assert msg.sender_type == 'client'
        assert msg.content == "Hello assistant"

        assert conv.messages.count() == 1


def test_generate_chatbot_reply_retrieval(app):
    """Test chatbot generates reply utilizing FAQ rules and pricing plans."""
    with app.app_context():
        lead = Lead(business_name="Nail Boutique", business_category="salon")
        db.session.add(lead)
        db.session.commit()

        # Seed KB and pricing
        kb = KnowledgeBase(category="company", title="Who is Flixora", content="Flixora is a premium design studio.")
        plan = PricingPlan(plan_name="Standard", price=199.0)
        db.session.add_all([kb, plan])
        
        # Seed settings
        set_name = Setting(category='agent', key='agent_name', value='Sophia')
        set_role = Setting(category='agent', key='agent_role', value='Representative')
        db.session.add_all([set_name, set_role])
        db.session.commit()

        conv = create_or_get_conversation(lead.id, 'whatsapp')
        
        mock_reply = "Flixora standard plans cost ₹199.0."
        with patch('app.services.conversation_service.llm_router.generate_text', return_value=mock_reply):
            res_msg = generate_chatbot_reply(conv.id, "How much is standard plan?")
            assert res_msg is not None
            assert res_msg.sender_type == 'ai'
            assert res_msg.sender_name == 'Sophia'
            assert "₹199.0" in res_msg.content


def test_human_takeover_pauses_chatbot(app):
    """Test taking over conversation pauses automatic AI chatbot replies."""
    with app.app_context():
        lead = Lead(business_name="Nail Boutique", business_category="salon")
        db.session.add(lead)
        db.session.commit()

        conv = create_or_get_conversation(lead.id, 'whatsapp')
        
        # Take over
        res = toggle_takeover_status(conv.id, active=True, admin_user_id=1)
        assert res['success'] is True
        assert res['status'] == ConversationStatus.ADMIN_ACTIVE

        # Verify AI generates nothing
        res_msg = generate_chatbot_reply(conv.id, "Hello chatbot")
        assert res_msg is None
