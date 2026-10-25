package dev.voxhash.ytscompanion.quest

import android.os.Bundle
import dev.voxhash.ytscompanion.R
import com.meta.spatial.core.Entity
import com.meta.spatial.core.Pose
import com.meta.spatial.core.Quaternion
import com.meta.spatial.core.SpatialFeature
import com.meta.spatial.core.Vector3
import com.meta.spatial.runtime.ReferenceSpace
import com.meta.spatial.toolkit.ActivityPanelRegistration
import com.meta.spatial.toolkit.AppSystemActivity
import com.meta.spatial.toolkit.DpPerMeterDisplayOptions
import com.meta.spatial.toolkit.PanelRegistration
import com.meta.spatial.toolkit.QuadShapeOptions
import com.meta.spatial.toolkit.Transform
import com.meta.spatial.toolkit.UIPanelSettings
import com.meta.spatial.toolkit.createPanelEntity
import com.meta.spatial.vr.VRFeature

/**
 * First immersive OpenXR / Meta Spatial SDK shell for Quest.
 *
 * Spawns a world-locked panel that hosts the same companion [MainActivity] UI
 * (queue / download / export). The 2D panel launcher remains available separately.
 * Not Horizon Store immersive certification.
 */
class ImmersiveShellActivity : AppSystemActivity() {
    override fun registerFeatures(): List<SpatialFeature> = listOf(VRFeature(this))

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }

    override fun onSceneReady() {
        super.onSceneReady()
        scene.setReferenceSpace(ReferenceSpace.LOCAL_FLOOR)
        // Stand in front of a floating companion panel.
        scene.setViewOrigin(0.0f, 0.0f, 0.0f, 0.0f)
        Entity.createPanelEntity(
            R.id.immersive_companion_panel,
            Transform(
                Pose(
                    Vector3(0.0f, 1.25f, -1.6f),
                    Quaternion(0f, 0f, 0f),
                ),
            ),
        )
    }

    override fun registerPanels(): List<PanelRegistration> {
        return listOf(
            ActivityPanelRegistration(
                R.id.immersive_companion_panel,
                classIdCreator = { MainActivity::class.java },
                settingsCreator = {
                    UIPanelSettings(
                        shape = QuadShapeOptions(width = 1.6f, height = 1.05f),
                        display = DpPerMeterDisplayOptions(),
                    )
                },
            ),
        )
    }
}
