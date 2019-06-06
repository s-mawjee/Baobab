
from datetime import datetime
import traceback

from flask import g, request
from flask_restful import reqparse, fields, marshal_with
import flask_restful as restful
from sqlalchemy.exc import SQLAlchemyError
from wtforms.validators import email

from app.events.models import Event, EventRole
from app.registration.models import Offer
from app.registration.mixins import RegistrationMixin
from app.users.models import AppUser, expiration_date
from app.users.repository import UserRepository as user_repository
from app.applicationModel.models import ApplicationForm
from app.responses.models import Response

from app import db, bcrypt, LOGGER
from app.utils import errors
from app.utils.errors import EVENT_NOT_FOUND, FORBIDDEN,FAILED_TO_ADD
from app.users import api as UserAPI
from app.users.mixins import SignupMixin

from app.utils.auth import auth_optional, auth_required, admin_required
from app.utils.emailer import send_mail


def offer_info(offerEntity):
    return {
        'user_id': offerEntity.user_id,
        'event_id':offerEntity.event_d,
        'offer_date':offerEntity.offer_date,
        'expiry_date':offerEntity.expiry_date,
        'payment_required':offerEntity.payment_required,
        'travel_award':offerEntity.travel_award,
        'accommodation_award':offerEntity.accomodation_award
    }

class OfferAPI(RegistrationMixin, restful.Resource):

    put_offer_fields =  {
        'user_id': fields.Integer,
        'accepted': fields.Boolean,
        'rejected': fields.Boolean,
        'rejected_reason': fields.String
    }

    @auth_required
    @marshal_with(put_offer_fields)
    def put(self):
        #update existing offer
        args = self.req_parser.parse_args()
        event_id = args['event_id']
        event_id = args['accepted']
        event_id = args['rejected']
        event_id = args['rejected_reason']
        try:
            event = db.session.query(Event).filter(Event.id == args['event_id']).first()
            db.session.commit()
            db.session.flush()
        except:
            LOGGER.error("Response not found for id {}".format(args['id']))
            return errors.RESPONSE_NOT_FOUND, 404


    @admin_required
    @marshal_with(offer_info)
    def post(self):
        args = self.req_parser.parse_args()
        user_id = g.current_user['id']
        email = g.current_user['email']
        event_id = args['event_id']
        offer_date = args['offer_date']
        expiry_date = args['expiry_date']
        payment_required = args['payment_required']
        travel_award = args['travel_award']
        accommodation_award = args['accommodation_award']

        user = db.session.query(AppUser).filter(AppUser.email == email).first()

        offerEntity = Offer(
            user_id = user_id,
            event_id = event_id,
            offer_date = offer_date,
            expiry_date = expiry_date,
            payment_required = payment_required,
            travel_award = travel_award,
            accommodation_award = accommodation_award
        )

        db.session.add(offerEntity)

        try:
            db.session.add(offerEntity)
            db.session.commit()
            #send an email confirmation
            self.send_confirmation(user, offer_info(offerEntity))
            return self.offer_info(offerEntity), 201
        except:
            LOGGER.error("Failed to add offer: {}",format(email))
            return FAILED_TO_ADD ,404


   #@marshal_with(offer_info)
    def get(self):
        args = self.req_parser.parse_args()
        event_id = args['event_id']

        user_id = g.current_user['id']
        try:
            event = db.session.query(Event).filter(Event.id == args['event_id']).first()
            if not event:
                LOGGER.warn("Event not found for event_id: {}".format(args['event_id']))
                return errors.EVENT_NOT_FOUND, 404
            return event
        except:
            LOGGER.error("Response not found for id {}".format(args['id']))
            return errors.RESPONSE_NOT_FOUND, 404


class CreateOfferAPI(SignupMixin, restful.Resource):

    @auth_required
    def post(self):
        user_api = UserAPI.UserAPI()
        return user_api.post(True)