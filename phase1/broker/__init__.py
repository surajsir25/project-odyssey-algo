"""Broker package."""

from .instrument_manager import InstrumentManager
from .upstox_client import UpstoxRestClient

__all__ = [
    "InstrumentManager",
    "UpstoxRestClient",
]
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def get_nifty_spot(self) -> Optional[InstrumentMaster]:
        """Get NIFTY spot instrument.
        
        Returns:
            InstrumentMaster for NIFTY spot index
        """
        query = select(InstrumentMaster).where(
            InstrumentMaster.symbol == "NIFTY",
            InstrumentMaster.option_type.is_(None),  # Spot has no option_type
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_nearest_weekly_expiry(self) -> Optional[date]:
        """Get nearest weekly expiry date.
        
        Returns:
            Nearest weekly expiry date
        """
        query = select(func.min(InstrumentMaster.expiry)).where(
            InstrumentMaster.expiry > datetime.utcnow().date(),
            InstrumentMaster.symbol == "NIFTY",
            InstrumentMaster.option_type.isnot(None),
        )
        result = await self.session.execute(query)
        return result.scalar()

    @staticmethod
    def calculate_atm_strike(spot_price: Decimal) -> Decimal:
        """Calculate ATM strike from spot price.
        
        NIFTY strikes are spaced by 50.
        Formula: atm = round(spot / 50) * 50
        
        Args:
            spot_price: Current spot price
            
        Returns:
            ATM strike price
        """
        return Decimal((int(spot_price) + 25) // 50 * 50)

    async def get_atm_ce(
        self, spot_price: Decimal, expiry: Optional[date] = None
    ) -> Optional[InstrumentMaster]:
        """Get ATM Call instrument.
        
        Args:
            spot_price: Current NIFTY spot price
            expiry: Expiry date (uses nearest weekly if not provided)
            
        Returns:
            InstrumentMaster for ATM CE
        """
        if expiry is None:
            expiry = await self.get_nearest_weekly_expiry()
        
        if expiry is None:
            logger.warning("No expiry available for ATM CE lookup")
            return None

        atm_strike = self.calculate_atm_strike(spot_price)
        
        query = select(InstrumentMaster).where(
            and_(
                InstrumentMaster.symbol == "NIFTY",
                InstrumentMaster.strike == atm_strike,
                InstrumentMaster.option_type == "CE",
                InstrumentMaster.expiry == expiry,
            )
        )
        result = await self.session.execute(query)
        instrument = result.scalars().first()
        
        if instrument is None:
            logger.warning(
                f"ATM CE not found - strike: {atm_strike}, expiry: {expiry}"
            )
        
        return instrument

    async def get_atm_pe(
        self, spot_price: Decimal, expiry: Optional[date] = None
    ) -> Optional[InstrumentMaster]:
        """Get ATM Put instrument.
        
        Args:
            spot_price: Current NIFTY spot price
            expiry: Expiry date (uses nearest weekly if not provided)
            
        Returns:
            InstrumentMaster for ATM PE
        """
        if expiry is None:
            expiry = await self.get_nearest_weekly_expiry()
        
        if expiry is None:
            logger.warning("No expiry available for ATM PE lookup")
            return None

        atm_strike = self.calculate_atm_strike(spot_price)
        
        query = select(InstrumentMaster).where(
            and_(
                InstrumentMaster.symbol == "NIFTY",
                InstrumentMaster.strike == atm_strike,
                InstrumentMaster.option_type == "PE",
                InstrumentMaster.expiry == expiry,
            )
        )
        result = await self.session.execute(query)
        instrument = result.scalars().first()
        
        if instrument is None:
            logger.warning(
                f"ATM PE not found - strike: {atm_strike}, expiry: {expiry}"
            )
        
        return instrument

    async def load_instrument_master(
        self, instruments: list[dict]
    ) -> int:
        """Load instrument master data from Upstox API.
        
        Args:
            instruments: List of instrument dicts from Upstox API
            
        Returns:
            Number of instruments loaded
        """
        # Delete old data for NIFTY only (preserve other instruments)
        await self.session.execute(
            f"DELETE FROM instrument_master WHERE symbol = 'NIFTY';"
        )
        await self.session.commit()
        
        count = 0
        for instrument_data in instruments:
            instrument = InstrumentMaster(
                instrument_key=instrument_data.get("instrument_key"),
                symbol=instrument_data.get("trading_symbol"),
                expiry=instrument_data.get("expiry"),
                strike=Decimal(str(instrument_data.get("strike", 0))),
                option_type=instrument_data.get("option_type"),
                exchange=instrument_data.get("exchange"),
            )
            self.session.add(instrument)
            count += 1
        
        await self.session.commit()
        logger.info(f"Loaded {count} instruments into master")
        
        return count

    async def get_instruments_by_symbol(self, symbol: str) -> list[InstrumentMaster]:
        """Get all instruments for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of InstrumentMaster records
        """
        query = select(InstrumentMaster).where(
            InstrumentMaster.symbol == symbol
        )
        result = await self.session.execute(query)
        return result.scalars().all()
