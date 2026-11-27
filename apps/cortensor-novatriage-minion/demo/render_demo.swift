import Foundation
import AVFoundation
import CoreGraphics
import ImageIO
import CoreMedia

@main
struct RenderNovaTriageDemo {
    static func loadCGImage(at path: String) throws -> CGImage {
        let url = URL(fileURLWithPath: path)
        guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
              let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
            throw NSError(domain: "RenderDemo", code: 1, userInfo: [NSLocalizedDescriptionKey: "Failed to load image at \(path)"])
        }
        return img
    }

    static func easeInOut(_ t: Double) -> Double {
        let x = max(0.0, min(1.0, t))
        return x < 0.5 ? 2.0 * x * x : 1.0 - pow(-2.0 * x + 2.0, 2.0) / 2.0
    }

    static func writeWavFile(to url: URL, totalSeconds: Double, sampleRate: Int = 44100) throws {
        let totalSamples = Int(totalSeconds * Double(sampleRate))
        var samples = [Int16](repeating: 0, count: totalSamples)
        let notes: [Double] = [329.63, 392.00, 440.00, 493.88, 523.25, 493.88, 440.00, 392.00]
        let beatInterval = 0.90

        for i in 0..<totalSamples {
            let t = Double(i) / Double(sampleRate)
            var val = 0.035 * sin(2.0 * .pi * 164.81 * t) + 0.025 * sin(2.0 * .pi * 246.94 * t)
            let currentBeat = Int(t / beatInterval)
            for b in max(0, currentBeat - 2)...currentBeat {
                let localT = t - Double(b) * beatInterval
                if localT >= 0 && localT < 1.5 {
                    let freq = notes[b % notes.count]
                    let attack = min(1.0, localT / 0.02)
                    let decay = exp(-localT * 3.0)
                    val += 0.11 * attack * decay * (sin(2.0 * .pi * freq * localT) + 0.2 * sin(2.0 * .pi * freq * 2.0 * localT))
                }
            }
            let fadeIn = min(1.0, t / 0.5)
            let fadeOut = min(1.0, max(0.0, (totalSeconds - t) / 0.8))
            let scaled = max(-0.92, min(0.92, val * fadeIn * fadeOut))
            samples[i] = Int16(scaled * Double(Int16.max))
        }

        let dataBytes = UInt32(totalSamples * 2)
        var wav = Data()
        wav.append("RIFF".data(using: .ascii)!)
        var chunkSize = (36 + dataBytes).littleEndian
        wav.append(Data(bytes: &chunkSize, count: 4))
        wav.append("WAVEfmt ".data(using: .ascii)!)
        var subchunk1: UInt32 = 16
        var audioFormat: UInt16 = 1
        var numChannels: UInt16 = 1
        var sr: UInt32 = UInt32(sampleRate)
        var byteRate: UInt32 = UInt32(sampleRate * 2)
        var blockAlign: UInt16 = 2
        var bitsPerSample: UInt16 = 16
        subchunk1 = subchunk1.littleEndian
        audioFormat = audioFormat.littleEndian
        numChannels = numChannels.littleEndian
        sr = sr.littleEndian
        byteRate = byteRate.littleEndian
        blockAlign = blockAlign.littleEndian
        bitsPerSample = bitsPerSample.littleEndian
        wav.append(Data(bytes: &subchunk1, count: 4))
        wav.append(Data(bytes: &audioFormat, count: 2))
        wav.append(Data(bytes: &numChannels, count: 2))
        wav.append(Data(bytes: &sr, count: 4))
        wav.append(Data(bytes: &byteRate, count: 4))
        wav.append(Data(bytes: &blockAlign, count: 2))
        wav.append(Data(bytes: &bitsPerSample, count: 2))
        wav.append("data".data(using: .ascii)!)
        var subchunk2 = dataBytes.littleEndian
        wav.append(Data(bytes: &subchunk2, count: 4))
        samples.withUnsafeBytes { ptr in
            wav.append(ptr.bindMemory(to: UInt8.self))
        }
        try wav.write(to: url)
    }

    static func drawScene(ctx: CGContext, img: CGImage, width: Int, height: Int, localProgress: Double, alpha: Double) {
        ctx.saveGState()
        ctx.setAlpha(alpha)
        let e = easeInOut(localProgress)
        let scale = 1.0 + 0.015 * e
        let drawW = Double(width) * scale
        let drawH = Double(height) * scale
        let dx = (Double(width) - drawW) / 2.0
        let dy = (Double(height) - drawH) / 2.0
        ctx.draw(img, in: CGRect(x: dx, y: dy, width: drawW, height: drawH))
        ctx.restoreGState()
    }

    static func drawProgressHUD(ctx: CGContext, width: Int, height: Int, frameIdx: Int, totalFrames: Int, sceneCount: Int, currentScene: Int) {
        let w = Double(width)
        let barY = 14.0
        let gap = 8.0
        let margin = 56.0
        let segW = (w - margin * 2.0 - gap * Double(sceneCount - 1)) / Double(sceneCount)
        let overall = Double(frameIdx) / Double(max(1, totalFrames - 1))

        for s in 0..<sceneCount {
            let x = margin + Double(s) * (segW + gap)
            ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 0.18))
            ctx.addPath(CGPath(roundedRect: CGRect(x: x, y: barY, width: segW, height: 4), cornerWidth: 2, cornerHeight: 2, transform: nil))
            ctx.fillPath()

            var fillFrac = 0.0
            if s < currentScene {
                fillFrac = 1.0
            } else if s == currentScene {
                let segSpan = 1.0 / Double(sceneCount)
                fillFrac = max(0.0, min(1.0, (overall - Double(s) * segSpan) / segSpan))
            }
            if fillFrac > 0.01 {
                ctx.setFillColor(CGColor(red: 0.22, green: 0.74, blue: 0.97, alpha: 0.95))
                ctx.addPath(CGPath(roundedRect: CGRect(x: x, y: barY, width: segW * fillFrac, height: 4), cornerWidth: 2, cornerHeight: 2, transform: nil))
                ctx.fillPath()
            }
        }
    }

    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())
        guard args.count >= 3 else {
            fputs("Usage: render_demo <output.mp4> <secPerScene> <scene1.png> [...]\n", stderr)
            exit(1)
        }
        let outputPath = args[0]
        let secPerScene = Double(args[1]) ?? 13.5
        let scenePaths = Array(args.dropFirst(2))

        do {
            let images = try scenePaths.map { try loadCGImage(at: $0) }
            let width = 1280
            let height = 720
            let fps: Int32 = 24
            let framesPerScene = Int(round(secPerScene * Double(fps)))
            let totalFrames = images.count * framesPerScene
            let totalSeconds = Double(totalFrames) / Double(fps)
            let fadeFrames = 12

            let outURL = URL(fileURLWithPath: outputPath)
            let dirURL = outURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: dirURL, withIntermediateDirectories: true)

            let tmpVideoURL = dirURL.appendingPathComponent(".tmp_\(outURL.lastPathComponent)")
            let tmpWavURL = dirURL.appendingPathComponent(".tmp_\(outURL.deletingPathExtension().lastPathComponent).wav")
            for u in [outURL, tmpVideoURL, tmpWavURL] {
                if FileManager.default.fileExists(atPath: u.path) {
                    try FileManager.default.removeItem(at: u)
                }
            }

            let writer = try AVAssetWriter(outputURL: tmpVideoURL, fileType: .mp4)
            let videoSettings: [String: Any] = [
                AVVideoCodecKey: AVVideoCodecType.h264,
                AVVideoWidthKey: width,
                AVVideoHeightKey: height,
                AVVideoCompressionPropertiesKey: [
                    AVVideoAverageBitRateKey: 450_000,
                    AVVideoMaxKeyFrameIntervalKey: 48
                ]
            ]
            let videoInput = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
            videoInput.expectsMediaDataInRealTime = false
            let pbAttrs: [String: Any] = [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                kCVPixelBufferWidthKey as String: width,
                kCVPixelBufferHeightKey as String: height
            ]
            let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: videoInput, sourcePixelBufferAttributes: pbAttrs)
            writer.add(videoInput)
            writer.startWriting()
            writer.startSession(atSourceTime: .zero)

            let colorSpace = CGColorSpaceCreateDeviceRGB()
            let bitmapInfo = CGBitmapInfo.byteOrder32Little.rawValue | CGImageAlphaInfo.premultipliedFirst.rawValue

            for f in 0..<totalFrames {
                while !videoInput.isReadyForMoreMediaData {
                    try await Task.sleep(nanoseconds: 2_000_000)
                }
                guard let pool = adaptor.pixelBufferPool else {
                    throw NSError(domain: "RenderDemo", code: 7, userInfo: [NSLocalizedDescriptionKey: "Missing pixelBufferPool"])
                }
                var maybePB: CVPixelBuffer?
                CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, pool, &maybePB)
                guard let pb = maybePB else {
                    throw NSError(domain: "RenderDemo", code: 8, userInfo: [NSLocalizedDescriptionKey: "Failed pixel buffer"])
                }

                autoreleasepool {
                    CVPixelBufferLockBaseAddress(pb, [])
                    if let ctx = CGContext(
                        data: CVPixelBufferGetBaseAddress(pb),
                        width: width,
                        height: height,
                        bitsPerComponent: 8,
                        bytesPerRow: CVPixelBufferGetBytesPerRow(pb),
                        space: colorSpace,
                        bitmapInfo: bitmapInfo
                    ) {
                        ctx.interpolationQuality = .high
                        let sceneIdx = min(images.count - 1, f / framesPerScene)
                        let localFrame = f % framesPerScene
                        let localProgress = Double(localFrame) / Double(max(1, framesPerScene - 1))

                        ctx.setFillColor(CGColor(red: 0.03, green: 0.05, blue: 0.09, alpha: 1.0))
                        ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))

                        if sceneIdx > 0 && localFrame < fadeFrames {
                            let prevAlpha = 1.0 - (Double(localFrame) / Double(fadeFrames))
                            drawScene(ctx: ctx, img: images[sceneIdx - 1], width: width, height: height, localProgress: 1.0, alpha: prevAlpha)
                            drawScene(ctx: ctx, img: images[sceneIdx], width: width, height: height, localProgress: localProgress, alpha: 1.0 - prevAlpha)
                        } else {
                            drawScene(ctx: ctx, img: images[sceneIdx], width: width, height: height, localProgress: localProgress, alpha: 1.0)
                        }

                        drawProgressHUD(ctx: ctx, width: width, height: height, frameIdx: f, totalFrames: totalFrames, sceneCount: images.count, currentScene: sceneIdx)
                    }
                    CVPixelBufferUnlockBaseAddress(pb, [])
                }

                let pts = CMTime(value: CMTimeValue(f), timescale: fps)
                adaptor.append(pb, withPresentationTime: pts)
            }

            videoInput.markAsFinished()
            await writer.finishWriting()
            try writeWavFile(to: tmpWavURL, totalSeconds: totalSeconds)

            let comp = AVMutableComposition()
            let vAsset = AVURLAsset(url: tmpVideoURL)
            let aAsset = AVURLAsset(url: tmpWavURL)
            let vTrack = try await vAsset.loadTracks(withMediaType: .video).first!
            let aTrack = try await aAsset.loadTracks(withMediaType: .audio).first!
            let compV = comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
            let compA = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
            let dur = CMTimeMinimum(try await vAsset.load(.duration), try await aAsset.load(.duration))
            try compV.insertTimeRange(CMTimeRange(start: .zero, duration: dur), of: vTrack, at: .zero)
            try compA.insertTimeRange(CMTimeRange(start: .zero, duration: dur), of: aTrack, at: .zero)

            let exporter = AVAssetExportSession(asset: comp, presetName: AVAssetExportPresetHighestQuality)!
            exporter.shouldOptimizeForNetworkUse = true
            try await exporter.export(to: outURL, as: .mp4)

            try? FileManager.default.removeItem(at: tmpVideoURL)
            try? FileManager.default.removeItem(at: tmpWavURL)

            let asset = AVURLAsset(url: outURL)
            let outDur = try await asset.load(.duration)
            let vTracks = try await asset.loadTracks(withMediaType: .video)
            let aTracks = try await asset.loadTracks(withMediaType: .audio)
            let size = try await vTracks.first?.load(.naturalSize) ?? .zero
            let attrs = try FileManager.default.attributesOfItem(atPath: outputPath)
            let bytes = (attrs[.size] as? NSNumber)?.int64Value ?? 0
            print(String(format: "[OK] %@ | duration=%.2fs | size=%.0fx%.0f | videoTracks=%d | audioTracks=%d | bytes=%lld",
                         outputPath, CMTimeGetSeconds(outDur), size.width, size.height, vTracks.count, aTracks.count, bytes))
        } catch {
            fputs("Error: \(error)\n", stderr)
            exit(1)
        }
    }
}
