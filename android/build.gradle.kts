plugins {
    // AGP 8.11.1 matches Meta Spatial SDK 0.14 plugin (requires Gradle 8.13+).
    id("com.android.application") version "8.11.1" apply false
    // Spatial SDK 0.14 plugin ships kotlin-compiler-embeddable 2.2.0 — match it.
    id("org.jetbrains.kotlin.android") version "2.2.0" apply false
    id("com.chaquo.python") version "17.1.0" apply false
    id("com.meta.spatial.plugin") version "0.14.0" apply false
}
