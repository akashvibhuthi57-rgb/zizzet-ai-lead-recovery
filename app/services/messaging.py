class MockMessagingProvider:
    """
    Mock messaging provider used for local development and testing.
    """

    def send_message(
        self,
        channel: str,
        phone: str,
        message: str,
    ) -> dict:
        """
        Simulate sending a message.
        No real message is sent.
        """

        return {
            "status": "sent",
            "channel": channel,
            "phone": phone,
            "message": message,
        }


messaging_provider = MockMessagingProvider()
