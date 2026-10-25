import SwiftUI

// v4c "Almanac" tokens. Fixed colors: the paper and the night stage never invert.

extension UIColor {
    convenience init(hex: UInt32, alpha: CGFloat = 1) {
        self.init(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                  blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
    }
}

extension Color {
    init(hex: UInt32, opacity: Double = 1) { self.init(UIColor(hex: hex, alpha: opacity)) }

    static let cream = Color(hex: 0xECE6DC)
    static let paper = Color(hex: 0xEEE8DE)
    static let taupe = Color(hex: 0xCFC6B8)
    static let fog = Color(hex: 0x8E8A84)
    static let ink = Color(hex: 0x1B1A18)
    static let night = Color(hex: 0x0B0B0A)
    static let soft = Color(hex: 0x6F6B65)
    static let sub = Color(hex: 0x77726B)
    static let muted = Color(hex: 0xA39D94)
    static let faint = Color(hex: 0xB9B3AA)
    static let later = Color(hex: 0xBDB7AE)
    static let rule = Color(hex: 0x1B1A18, opacity: 0.13)
    static let ribbon = Color(hex: 0x82342C)
    static let madder = Color(hex: 0x8C3B32, opacity: 0.26)
    static let rec = Color(hex: 0xB23A2E)
    static let lamp = Color(hex: 0xF6E7C8)
    static let words = Color(hex: 0xD9D3C9)
    static let wordsEm = Color(hex: 0xA39E96)

    /// Hearth fallback shim.
    static let ember = lamp
}

extension Font {
    static func serif(_ size: CGFloat, relativeTo style: TextStyle = .body) -> Font {
        .custom("InstrumentSerif-Regular", size: size, relativeTo: style)
    }

    static func serifItalic(_ size: CGFloat, relativeTo style: TextStyle = .body) -> Font {
        .custom("InstrumentSerif-Italic", size: size, relativeTo: style)
    }

    static func sans(_ size: CGFloat, medium: Bool = false) -> Font {
        .custom(medium ? "Inter-Medium" : "Inter-Regular", size: size, relativeTo: .caption)
    }

    static func sansLight(_ size: CGFloat) -> Font {
        .custom("Inter-Light", fixedSize: size)
    }

    /// Hearth fallback shim.
    static func display(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .custom("InstrumentSerif-Regular", fixedSize: size)
    }
}

struct Hairline: View {
    var color: Color = .rule
    var body: some View {
        Rectangle().fill(color).frame(height: 1 / UIScreen.main.scale * 2).frame(maxWidth: .infinity)
            .accessibilityHidden(true)
    }
}

/// Italic emphasis from `*marked*` spans, set in the italic cut.
func emphasized(_ text: String, size: CGFloat, color: Color, emColor: Color) -> Text {
    var out = Text("")
    for (i, part) in text.split(separator: "*", omittingEmptySubsequences: false).enumerated() where !part.isEmpty {
        let em = i % 2 == 1
        out = out + Text(String(part)).font(em ? .serifItalic(size) : .serif(size)).foregroundColor(em ? emColor : color)
    }
    return out
}

extension String {
    var unmarked: String { replacingOccurrences(of: "*", with: "") }
}

// Use ease-out curves only.

extension Animation {
    static let enter = Animation.timingCurve(0.23, 1, 0.32, 1, duration: 0.6)
    static let exit = Animation.timingCurve(0.23, 1, 0.32, 1, duration: 0.3)
    static let press = Animation.timingCurve(0.23, 1, 0.32, 1, duration: 0.16)
    static let gentle = enter
}

extension AnyTransition {
    static var fade: AnyTransition {
        .asymmetric(insertion: .opacity.animation(.enter), removal: .opacity.animation(.exit))
    }
}

@MainActor
enum PaperGrain {
    static let image: UIImage = {
        let side = 240
        var rng = SeededRandom(seed: 1987)
        var pixels = [UInt8](repeating: 0, count: side * side)
        for i in pixels.indices {
            let a = Int(rng.next() % 256), b = Int(rng.next() % 256)
            pixels[i] = UInt8(clamping: (a + b) / 2)
        }
        let provider = CGDataProvider(data: Data(pixels) as CFData)!
        let cg = CGImage(width: side, height: side, bitsPerComponent: 8, bitsPerPixel: 8, bytesPerRow: side,
                         space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGBitmapInfo(rawValue: 0),
                         provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
        return UIImage(cgImage: cg, scale: 2, orientation: .up)
    }()
}

struct GrainOverlay: View {
    var opacity: Double = 0.5
    var body: some View {
        Image(uiImage: PaperGrain.image)
            .resizable(resizingMode: .tile)
            .blendMode(.overlay)
            .opacity(opacity)
            .allowsHitTesting(false)
            .accessibilityHidden(true)
    }
}

/// Cream page with grain, a binding shadow at the spine and page edges at the fore edge.
struct PaperCanvas: View {
    var body: some View {
        Color.paper
            .overlay(alignment: .leading) {
                LinearGradient(stops: [.init(color: Color(hex: 0x463422, opacity: 0.16), location: 0),
                                       .init(color: Color(hex: 0x463422, opacity: 0.05), location: 0.4),
                                       .init(color: .clear, location: 1)],
                               startPoint: .leading, endPoint: .trailing)
                    .frame(width: 26)
            }
            .overlay(alignment: .trailing) {
                HStack(spacing: 1) {
                    ForEach(0..<3, id: \.self) { _ in Color(hex: 0x5A4834, opacity: 0.12).frame(width: 1) }
                }
                .frame(width: 5, alignment: .trailing)
            }
            .overlay { GrainOverlay(opacity: 0.35) }
            .compositingGroup()
            .ignoresSafeArea()
            .allowsHitTesting(false)
            .accessibilityHidden(true)
    }
}

struct NightCanvas: View {
    var body: some View {
        Color.night
            .overlay {
                Image(uiImage: PaperGrain.image)
                    .resizable(resizingMode: .tile)
                    .blendMode(.screen)
                    .opacity(0.06)
            }
            .ignoresSafeArea()
            .allowsHitTesting(false)
            .accessibilityHidden(true)
    }
}

struct Vignette: View {
    var body: some View {
        RadialGradient(stops: [.init(color: .clear, location: 0.55), .init(color: .black.opacity(0.5), location: 1)],
                       center: UnitPoint(x: 0.5, y: 0.4), startRadius: 0, endRadius: 560)
            .ignoresSafeArea()
            .allowsHitTesting(false)
            .accessibilityHidden(true)
    }
}

struct SeededRandom {
    private var state: UInt64
    init(seed: UInt64) { state = seed &* 6364136223846793005 &+ 1 }
    mutating func next() -> UInt64 {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        return state >> 33
    }
}

struct PressStyle: ButtonStyle {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .opacity(configuration.isPressed ? 0.6 : 1)
            .scaleEffect(configuration.isPressed && !reduceMotion ? 0.98 : 1)
            .animation(.press, value: configuration.isPressed)
    }
}

/// Flat dark rectangle, the one primary action on a page.
struct SlabButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.serif(21))
            .foregroundStyle(Color.cream)
            .lineLimit(1)
            .minimumScaleFactor(0.8)
            .frame(maxWidth: .infinity, minHeight: 58)
            .background(Color.ink.opacity(configuration.isPressed ? 0.85 : 1), in: .rect(cornerRadius: 4))
            .animation(.press, value: configuration.isPressed)
    }
}

struct RecordDisc: View {
    var live: Bool
    var body: some View {
        Circle()
            .fill(Color.ink)
            .overlay(Circle().strokeBorder(.black.opacity(0.4), lineWidth: 2).blur(radius: 2).offset(y: -1).mask(Circle()))
            .overlay {
                Circle().fill(Color.rec)
                    .frame(width: live ? 26 : 22, height: live ? 26 : 22)
                    .overlay(Circle().stroke(Color(hex: 0xFFDCC8, opacity: 0.25), lineWidth: 1).offset(y: 0.5).mask(Circle()))
            }
            .frame(width: 72, height: 72)
            .shadow(color: Color(hex: 0x1E140A, opacity: 0.45), radius: 9, y: 10)
            .animation(.enter, value: live)
    }
}

/// Blinking caret for live writing. Holds still under Reduce Motion.
struct Caret: View {
    var height: CGFloat = 28
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var on = true
    var body: some View {
        Rectangle().fill(Color.ink).frame(width: 1.5, height: height)
            .opacity(on ? 1 : 0)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 0.55).repeatForever(autoreverses: true)) { on = false }
            }
            .accessibilityHidden(true)
    }
}

/// Slow pan over an image. Hearth fallback only.
struct KenBurns<Content: View>: View {
    @ViewBuilder var content: Content
    @State private var forward = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        GeometryReader { geo in
            content
                .frame(width: geo.size.width, height: geo.size.height)
                .scaleEffect(forward ? 1.18 : 1.1)
                .clipped()
                .onAppear {
                    guard !reduceMotion else { return }
                    withAnimation(.easeInOut(duration: 24).repeatForever(autoreverses: true)) { forward = true }
                }
        }
        .ignoresSafeArea()
    }
}

func formatDuration(_ t: TimeInterval) -> String {
    let s = max(0, Int(t.rounded(.down)))
    return String(format: "%d:%02d", s / 60, s % 60)
}

func languageName(_ code: String) -> String {
    switch code {
    case "es": "Spanish"
    case "en": "English"
    default: Locale.current.localizedString(forLanguageCode: code) ?? code
    }
}

/// A language named in its own tongue, lowercase like the diary writes it.
func endonym(_ code: String) -> String {
    switch code {
    case "es": "español"
    case "en": "English"
    default: Locale(identifier: code).localizedString(forLanguageCode: code) ?? code
    }
}

extension View {
    /// Debug screenshots only: `-screenshotBottom YES` opens long screens at the end.
    @ViewBuilder func screenshotAnchor() -> some View {
        #if DEBUG
        defaultScrollAnchor(UserDefaults.standard.bool(forKey: "screenshotBottom") ? .bottom : .top)
        #else
        self
        #endif
    }
}
