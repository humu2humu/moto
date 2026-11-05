package dev.moto.spots

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class SpotFinderTest {

    private val origin = GeoPoint(35.0, 139.0)

    private fun spot(id: String, category: SpotCategory, lat: Double, lon: Double) =
        Spot(id, id, category, GeoPoint(lat, lon), "addr")

    private val finder = SpotFinder {
        listOf(
            spot("far", SpotCategory.FUEL, 35.10, 139.0),
            spot("near", SpotCategory.FUEL, 35.01, 139.0),
            spot("mid", SpotCategory.FUEL, 35.05, 139.0),
            spot("parking", SpotCategory.MOTO_PARKING, 35.001, 139.0),
        )
    }

    @Test
    fun `filters by category and sorts by distance`() {
        val ids = finder.nearby(origin, SpotCategory.FUEL).map { it.spot.id }
        assertEquals(listOf("near", "mid", "far"), ids)
    }

    @Test
    fun `respects limit and max distance`() {
        assertEquals(listOf("near"), finder.nearby(origin, SpotCategory.FUEL, limit = 1).map { it.spot.id })
        val within = finder.nearby(origin, SpotCategory.FUEL, maxDistanceMeters = 6_000.0).map { it.spot.id }
        assertEquals(listOf("near", "mid"), within)
    }

    @Test
    fun `ties are broken by id for stable ordering`() {
        val tied = SpotFinder {
            listOf(spot("b", SpotCategory.REST, 35.01, 139.0), spot("a", SpotCategory.REST, 35.01, 139.0))
        }
        assertEquals(listOf("a", "b"), tied.nearby(origin, SpotCategory.REST).map { it.spot.id })
    }

    @Test
    fun `empty result when nothing matches`() {
        assertTrue(finder.nearby(origin, SpotCategory.REST).isEmpty())
        assertTrue(finder.nearby(origin, SpotCategory.FUEL, limit = 0).isEmpty())
    }

    @Test
    fun `rejects invalid arguments`() {
        assertFailsWith<IllegalArgumentException> { finder.nearby(origin, SpotCategory.FUEL, limit = -1) }
        assertFailsWith<IllegalArgumentException> { finder.nearby(origin, SpotCategory.FUEL, maxDistanceMeters = -1.0) }
    }

    @Test
    fun `sample data has every category near the default origin`() {
        val sampleFinder = SpotFinder(SampleSpots)
        for (category in SpotCategory.entries) {
            val result = sampleFinder.nearby(SampleSpots.DEFAULT_ORIGIN, category, maxDistanceMeters = 5_000.0)
            assertTrue(result.isNotEmpty(), "no sample spot for $category")
        }
        assertEquals(SampleSpots.all().size, SampleSpots.all().map { it.id }.toSet().size, "duplicate ids")
    }
}
