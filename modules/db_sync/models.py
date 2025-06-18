from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    
    rma_requests = relationship("RMARequest", back_populates="customer")

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    serial_number = Column(String(100))
    description = Column(Text)
    
    rma_requests = relationship("RMARequest", back_populates="product")

class RepairCenter(Base):
    __tablename__ = 'repair_centers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    contact_info = Column(Text)
    
    rma_requests = relationship("RMARequest", back_populates="repair_center")

class ShippingStatus(enum.Enum):
    """Mögliche Status für Sendungen."""
    LABEL_CREATED = "Label ausgestellt"
    IN_TRANSIT = "Versendet"
    DELIVERED = "Zugestellt"
    DELIVERED_TO_NEIGHBOR = "Bei Nachbarn"
    UNKNOWN = "Unbekannt"

class RMARequest(Base):
    __tablename__ = 'rma_requests'
    
    id = Column(Integer, primary_key=True)
    rma_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    repair_center_id = Column(Integer, ForeignKey('repair_centers.id'))
    date_created = Column(DateTime)
    date_updated = Column(DateTime)
    status = Column(String(50))
    description = Column(Text)
    
    customer = relationship("Customer", back_populates="rma_requests")
    product = relationship("Product", back_populates="rma_requests")
    repair_center = relationship("RepairCenter", back_populates="rma_requests")
    repair_status = relationship("RepairStatus", back_populates="rma_request")
    repair_notes = relationship("RepairNote", back_populates="rma_request")
    shipping = relationship("Shipping", back_populates="rma_request")
    attachments = relationship("Attachment", back_populates="rma_request")

    def update_status(self, new_status: str) -> None:
        """Aktualisiert den Status der RMA-Anfrage.
        
        Args:
            new_status: Der neue Status (muss einem ShippingStatus entsprechen)
        """
        valid_statuses = [status.value for status in ShippingStatus]
        if new_status not in valid_statuses:
            raise ValueError(f"Ungültiger Status. Erlaubte Werte: {valid_statuses}")
        self.status = new_status

class RepairStatus(Base):
    __tablename__ = 'repair_status'
    
    id = Column(Integer, primary_key=True)
    rma_request_id = Column(Integer, ForeignKey('rma_requests.id'))
    status = Column(String(50))
    date_updated = Column(DateTime)
    notes = Column(Text)
    
    rma_request = relationship("RMARequest", back_populates="repair_status")

class RepairNote(Base):
    __tablename__ = 'repair_notes'
    
    id = Column(Integer, primary_key=True)
    rma_request_id = Column(Integer, ForeignKey('rma_requests.id'))
    note = Column(Text)
    date_created = Column(DateTime)
    created_by = Column(String(100))
    
    rma_request = relationship("RMARequest", back_populates="repair_notes")

class Shipping(Base):
    __tablename__ = 'shipping'
    
    id = Column(Integer, primary_key=True)
    rma_request_id = Column(Integer, ForeignKey('rma_requests.id'))
    tracking_number = Column(String(100))
    carrier = Column(String(50))
    date_shipped = Column(DateTime)
    date_received = Column(DateTime)
    status = Column(Enum(ShippingStatus), default=ShippingStatus.UNKNOWN)
    last_tracking_update = Column(DateTime)
    tracking_details = Column(Text)  # Für zusätzliche Tracking-Informationen
    
    rma_request = relationship("RMARequest", back_populates="shipping")

class Attachment(Base):
    __tablename__ = 'attachments'
    
    id = Column(Integer, primary_key=True)
    rma_request_id = Column(Integer, ForeignKey('rma_requests.id'))
    file_name = Column(String(255))
    file_path = Column(String(255))
    date_uploaded = Column(DateTime)
    
    rma_request = relationship("RMARequest", back_populates="attachments") 