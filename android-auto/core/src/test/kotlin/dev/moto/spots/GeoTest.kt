package dev.moto.spots

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class GeoTest {

    @Test
    fun `distance between same point is zero`() {
        val p = GeoPoint(35.6812, 139.7671)
        assertEquals(0.0, distanceMeters(p, p), 1e-9)
    }

    @Test
    fun `one degree of latitude is about 111 km`() {
        val d = distanceMeters(GeoPoint(35.0, 139.0), GeoPoint(36.0, 139.0))
        assertEquals(111_195.0, d, 50.0)
    }

    @Test
    fun `antipodal points do not produce NaN`() {
        val d = distanceMeters(GeoPoint(0.0, 0.0), GeoPoint(0.0, 180.0))
        assertEquals(Math.PI * 6_371_000.0, d, 1.0)
    }

    @Test
    fun `rejects out of range coordinates`() {
        assertFailsWith<IllegalArgumentException> { GeoPoint(91.0, 0.0) }
        assertFailsWith<IllegalArgumentException> { GeoPoint(0.0, -181.0) }
    }

    @Test
    fun `display distance picks readable units`() {
        assertEquals(DisplayDistance(0.0, DistanceUnit.METERS), toDisplayDistance(0.0))
        assertEquals(DisplayDistance(340.0, DistanceUnit.METERS), toDisplayDistance(336.0))
        assertEquals(DisplayDistance(990.0, DistanceUnit.METERS), toDisplayDistance(994.0))
        // 995 m は 10 m 丸めで 1000 m になるので km 表示に切り替える(「1000 m」とは出さない)。
        assertEquals(DisplayDistance(1.0, DistanceUnit.KILOMETERS_ONE_DECIMAL), toDisplayDistance(995.0))
        assertEquals(DisplayDistance(2.4, DistanceUnit.KILOMETERS_ONE_DECIMAL), toDisplayDistance(2_440.0))
        assertEquals(DisplayDistance(9.9, DistanceUnit.KILOMETERS_ONE_DECIMAL), toDisplayDistance(9_940.0))
        // 9.95 km 以上は「10.0 km」ではなく整数 km。
        assertEquals(DisplayDistance(10.0, DistanceUnit.KILOMETERS), toDisplayDistance(9_950.0))
        assertEquals(DisplayDistance(15.0, DistanceUnit.KILOMETERS), toDisplayDistance(15_400.0))
    }

    @Test
    fun `format distance`() {
        assertEquals("340 m", formatDistance(336.0))
        assertEquals("1.0 km", formatDistance(995.0))
        assertEquals("2.4 km", formatDistance(2_440.0))
        assertEquals("15 km", formatDistance(15_400.0))
    }

    @Test
    fun `display distance rejects invalid input`() {
        assertFailsWith<IllegalArgumentException> { toDisplayDistance(-1.0) }
        assertFailsWith<IllegalArgumentException> { toDisplayDistance(Double.NaN) }
    }
}
