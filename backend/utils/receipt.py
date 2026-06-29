import logging
from typing import Dict
from datetime import datetime
from chatbot.supabase_config import supabase

logger = logging.getLogger(__name__)

class ReceiptGenerator:
    @staticmethod
    def generate_html_receipt(payment_data: Dict, appointment_data: Dict, clinic_data: Dict, owner_name: str) -> str:
        """
        Generates a beautiful HTML invoice/receipt.
        """
        created_date = datetime.fromisoformat(payment_data["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.4; }}
                .invoice-box {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0, 0, 0, .15); font-size: 16px; }}
                .invoice-box table {{ w-full: 100%; text-align: left; border-collapse: collapse; width: 100%; }}
                .invoice-box table td {{ padding: 5px; vertical-align: top; }}
                .invoice-box table tr td:nth-child(2) {{ text-align: right; }}
                .invoice-box table tr.top table td {{ padding-bottom: 20px; }}
                .invoice-box table tr.top table td.title {{ font-size: 45px; line-height: 45px; color: #0D9488; font-weight: bold; }}
                .invoice-box table tr.information table td {{ padding-bottom: 40px; }}
                .invoice-box table tr.heading td {{ bg-color: #eee; background: #f8fafc; border-bottom: 1px solid #ddd; font-weight: bold; padding: 10px; }}
                .invoice-box table tr.item td{{ border-bottom: 1px solid #eee; padding: 10px; }}
                .invoice-box table tr.total td:nth-child(2) {{ border-top: 2px solid #eee; font-weight: bold; font-size: 18px; color: #0D9488; }}
                .badge {{ padding: 4px 8px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: #dcfce7; color: #15803d; }}
            </style>
        </head>
        <body>
            <div class="invoice-box">
                <table>
                    <tr class="top">
                        <td colspan="2">
                            <table>
                                <tr>
                                    <td class="title">PetPULSE</td>
                                    <td>
                                        Receipt #: {payment_data["id"][:8].upper()}<br>
                                        Created: {created_date}<br>
                                        Status: <span class="badge">PAID</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <tr class="information">
                        <td colspan="2">
                            <table>
                                <tr>
                                    <td>
                                        <strong>Billing To:</strong><br>
                                        {owner_name}<br>
                                        Patient: {appointment_data.get("pet_name", "Pet")}
                                    </td>
                                    <td>
                                        <strong>Clinic:</strong><br>
                                        {clinic_data.get("clinic_name")}<br>
                                        {clinic_data.get("address", "")}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <tr class="heading">
                        <td>Payment Method</td>
                        <td>Transaction ID</td>
                    </tr>
                    <tr class="details">
                        <td>Stripe Checkout (Card)</td>
                        <td>{payment_data.get("payment_intent_id", "N/A")}</td>
                    </tr>
                    
                    <tr class="heading">
                        <td>Service Description</td>
                        <td>Price</td>
                    </tr>
                    <tr class="item">
                        <td>Veterinary Consultation ({appointment_data.get("reason", "General Checkup")})</td>
                        <td>LKR {payment_data["amount"]:.2f}</td>
                    </tr>
                    
                    <tr class="total">
                        <td></td>
                        <td>Total: LKR {payment_data["amount"]:.2f}</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        """
        return html_content

    @staticmethod
    async def create_and_upload_receipt(payment_id: str) -> Optional[str]:
        """
        Compiles the receipt HTML and uploads it to Supabase Storage.
        Returns the public URL of the receipt.
        """
        try:
            # 1. Fetch payment and related data
            pay_resp = supabase.table("payments").select("*").eq("id", payment_id).execute()
            if not pay_resp.data:
                return None
            payment = pay_resp.data[0]
            
            appt_resp = supabase.table("appointments").select("*, pets(name)").eq("id", payment["appointment_id"]).execute()
            if not appt_resp.data:
                return None
            appointment = appt_resp.data[0]
            appointment["pet_name"] = appointment.get("pets", {}).get("name", "Pet")

            clinic_resp = supabase.table("clinics").select("*").eq("id", appointment["clinic_id"]).execute()
            clinic = clinic_resp.data[0] if clinic_resp.data else {}

            owner_resp = supabase.table("users").select("full_name").eq("id", appointment["owner_id"]).execute()
            owner_name = owner_resp.data[0].get("full_name", "Pet Owner") if owner_resp.data else "Pet Owner"

            # 2. Generate HTML
            html_receipt = ReceiptGenerator.generate_html_receipt(payment, appointment, clinic, owner_name)
            
            # 3. Upload to Supabase Storage Bucket 'receipts'
            file_name = f"receipts/{payment_id}.html"
            
            # Note: We upload as text/html. In production, you would convert to PDF binary here
            # and upload with content_type="application/pdf"
            supabase.storage.from_("receipts").upload(
                path=file_name,
                file=html_receipt.encode('utf-8'),
                file_options={"content-type": "text/html", "x-upsert": "true"}
            )
            
            # 4. Get Public URL
            public_url = supabase.storage.from_("receipts").get_public_url(file_name)
            
            # 5. Update payment record with the URL
            supabase.table("payments").update({"receipt_url": public_url}).eq("id", payment_id).execute()
            
            return public_url
        except Exception as e:
            logger.error(f"Failed to generate/upload receipt: {str(e)}")
            return None
