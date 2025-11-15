// src/components/HoloCard.jsx

import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

// Shaders (vertexShader, fragmentShader) permanecem os mesmos
const vertexShader = `
  uniform vec2 uCardDimensions;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vViewDirection;

  void main() {
    vUv.x = (position.x + uCardDimensions.x / 2.0) / uCardDimensions.x;
    vUv.y = (position.y + uCardDimensions.y / 2.0) / uCardDimensions.y;

    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vNormal = normalize(normalMatrix * normal);
    vViewDirection = normalize(cameraPosition - worldPosition.xyz);
    
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = `
  uniform sampler2D uCardTexture;
  uniform sampler2D uFoilTexture;
  uniform vec2 uMouse;
  uniform float uTime;
  
  uniform int uEffectId;
  uniform float uParam1; uniform float uParam2; uniform float uParam3;
  uniform float uParam4; uniform float uParam5; uniform float uParam6;
  uniform float uParam7; uniform float uParam8; uniform float uParam9;
  uniform float uParam10;

  uniform int uColorMode;
  uniform vec3 uColor1; uniform vec3 uColor2;
  uniform float uGradientAngle; uniform float uGradientScale;
  uniform vec3 uLightDirection;

  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vViewDirection;

  vec3 hsl2rgb(vec3 c) {
    vec3 rgb = clamp(abs(mod(c.x*6.0+vec3(0.0,4.0,2.0), 6.0)-3.0)-1.0, 0.0, 1.0);
    return c.z + c.y * (rgb-0.5)*(1.0-abs(2.0*c.z-1.0));
  }
  
  vec3 getHoloBaseColor(float hueDrive) {
    if (uColorMode == 0) {
      return hsl2rgb(vec3(hueDrive, 0.8, 0.55));
    } else {
      return mix(uColor1, uColor2, hueDrive);
    }
  }

  void main() {
    vec4 cardColor = texture2D(uCardTexture, vUv);
    vec3 finalColor = cardColor.rgb;
    vec3 holoColor = vec3(0.0);

    vec2 mouseUv = vec2(uMouse.x * 0.5 + 0.5, uMouse.y * 0.5 + 0.5);
    float glareDist = distance(vUv, mouseUv);
    
    vec3 reflection = reflect(-uLightDirection, vNormal);
    
    float angleRad = uGradientAngle * 3.14159 / 180.0;
    vec2 direction = vec2(cos(angleRad), sin(angleRad));
    float gradientDrive = clamp(dot(normalize(vNormal.xy), direction) * uGradientScale + 0.5, 0.0, 1.0);
    float rainbowDrive = fract(vUv.x * 1.0 - vUv.y * 0.5 + (vNormal.x + vNormal.y) * 2.5);

    if (uEffectId == 4) {
        float patternScale = uParam1; float reflectivity = uParam2;
        float cursorIntensity = uParam3; float ambientIntensity = uParam4;
        float cursorSize = uParam5; float holoMainLightResponse = uParam6;
        float holoGlow = uParam7; float specularSharpness = uParam8;
        float rimLightIntensity = uParam9; float parallaxStrength = uParam10;
        
        vec2 parallaxOffset = vViewDirection.xy * parallaxStrength;
        vec2 patternUv = vUv * patternScale + parallaxOffset;
        float pattern = texture2D(uFoilTexture, patternUv).r;

        float mainLightSpecular = pow(max(0.0, dot(reflection, vViewDirection)), 16.0) * holoMainLightResponse;
        float specSharpness = 16.0 + specularSharpness * 240.0;
        float directionalSpecular = pow(max(0.0, dot(reflection, vViewDirection)), specSharpness); 
        float fresnel = pow(1.0 - max(0.0, dot(vViewDirection, vNormal)), 3.0) * rimLightIntensity;
        
        float cursorArea = 0.05 + cursorSize * 0.4;
        float mouseLight = pow(1.0 - smoothstep(0.0, cursorArea, glareDist), 2.0) * cursorIntensity;
        
        float baseIllumination = (mainLightSpecular + directionalSpecular + fresnel + mouseLight) * pattern;
        float reflectedIllumination = baseIllumination * reflectivity;
        float glow = pow(reflectedIllumination, 4.0) * holoGlow * 10.0;
        float finalIllumination = reflectedIllumination + glow;

        float hueDrive = (uColorMode == 0) ? rainbowDrive : gradientDrive;
        holoColor += getHoloBaseColor(hueDrive) * finalIllumination;
    }

    vec3 ambient = vec3(uParam4 * 0.7);
    float diffuseFactor = max(0.0, dot(vNormal, uLightDirection));
    vec3 diffuse = vec3(uParam4 * 0.3) * diffuseFactor;

    finalColor = cardColor.rgb * (ambient + diffuse) + holoColor;
    
    gl_FragColor = vec4(finalColor, cardColor.a);
  }
`;

const easeInOutSine = (x) => -(Math.cos(Math.PI * x) - 1) / 2;

const ANIMATION_CONFIG = {
    MOUSE_ROTATION_SENSITIVITY: 0.3,
    TARGET_DAMPING_FACTOR: 0.08,
    ROTATION_DAMPING_FACTOR: 0.1,
    CURSOR_LIGHT_FADE_SPEED: 0.1,
    IDLE_MAX_ROTATION_ANGLE: 0.3,
    IDLE_TURN_DURATION: 2,
    IDLE_PAUSE_DURATION: 0.0,
};

const HoloCard = ({ imageUrl, title }) => {
    const mountRef = useRef(null);
    const isHoveringRef = useRef(false);
    const clockRef = useRef(new THREE.Clock());

    // Parâmetros e conteúdo do cartão (sem alterações)
    const effectParams = {
        patternScale: 1.00, reflectivity: 2.17, cursorIntensity: 0.3,
        ambientIntensity: 1.00, cursorSize: 1.0, holoMainLightResponse: 1.1,
        holoGlow: 2.62, specularSharpness: 0.44, rimLightIntensity: 0.31,
        parallaxStrength: 0.27,
    };
    const gradientParams = { angle: 45, scale: 1.01 };
    const foilUrl = 'https://i.imgur.com/uJjQcme.png';
    const colorMode = 'gradient';
    const color1 = '#ff00ff';
    const color2 = '#00ffff';
    const cardContent = {
        leagueName: title || 'Generated Art', placement: 'DIGITAL MUSEUM',
        playerName: 'LUMITY', date: new Date().toLocaleDateString('pt-BR'),
    };

    useEffect(() => {
        if (!mountRef.current) return;
        const currentMount = mountRef.current;

        // Configuração da cena, câmera, renderer, etc. (sem alterações)
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, currentMount.clientWidth / currentMount.clientHeight, 0.1, 1000);
        camera.position.z = 1.3;
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(currentMount.clientWidth, currentMount.clientHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        currentMount.appendChild(renderer.domElement);
        
        const cardWidth = 1.4*0.8;
        const cardHeight = 1.95*0.8;

        const canvas = document.createElement('canvas');
        canvas.width = 1260;
        canvas.height = 1760;
        const canvasTexture = new THREE.CanvasTexture(canvas);

        const foilTextureLoader = new THREE.TextureLoader();
        const loadedFoilTexture = foilTextureLoader.load(foilUrl, (texture) => {
            texture.wrapS = THREE.RepeatWrapping;
            texture.wrapT = THREE.RepeatWrapping;
        });

        const uniforms = {
            uTime: { value: 0.0 }, uMouse: { value: new THREE.Vector2(0, 0) },
            uCardDimensions: { value: new THREE.Vector2(cardWidth, cardHeight) },
            uCardTexture: { value: canvasTexture }, uFoilTexture: { value: loadedFoilTexture },
            uEffectId: { value: 4 }, uParam1: { value: effectParams.patternScale },
            uParam2: { value: effectParams.reflectivity }, uParam3: { value: effectParams.cursorIntensity },
            uParam4: { value: effectParams.ambientIntensity }, uParam5: { value: effectParams.cursorSize },
            uParam6: { value: effectParams.holoMainLightResponse }, uParam7: { value: effectParams.holoGlow },
            uParam8: { value: effectParams.specularSharpness }, uParam9: { value: effectParams.rimLightIntensity },
            uParam10: { value: effectParams.parallaxStrength }, uColorMode: { value: colorMode === 'gradient' ? 1 : 0 },
            uColor1: { value: new THREE.Color(color1) }, uColor2: { value: new THREE.Color(color2) },
            uGradientAngle: { value: gradientParams.angle }, uGradientScale: { value: gradientParams.scale },
            uLightDirection: { value: new THREE.Vector3(0, 0, 1).normalize() },
        };
        
        const createRoundedRectShape = (width, height, radius) => {
            const shape = new THREE.Shape();
            const x = -width / 2, y = -height / 2;
            shape.moveTo(x, y + radius); shape.lineTo(x, y + height - radius);
            shape.quadraticCurveTo(x, y + height, x + radius, y + height);
            shape.lineTo(x + width - radius, y + height);
            shape.quadraticCurveTo(x + width, y + height, x + width, y + height - radius);
            shape.lineTo(x + width, y + radius);
            shape.quadraticCurveTo(x + width, y, x + width - radius, y);
            shape.lineTo(x + radius, y);
            shape.quadraticCurveTo(x, y, x, y + radius);
            return shape;
        }
        
        const cardGeometry = new THREE.ShapeGeometry(createRoundedRectShape(cardWidth, cardHeight, 0.07), 64);
        const cardMaterial = new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, transparent: true });
        const cardMesh = new THREE.Mesh(cardGeometry, cardMaterial);
        scene.add(cardMesh);

        const mousePos = new THREE.Vector2(0, 0);
        const finalTargetRotation = new THREE.Vector2(0, 0);
        const smoothTargetRotation = new THREE.Vector2(0, 0);

        const handleMouseMove = (event) => {
            const rect = currentMount.getBoundingClientRect();
            mousePos.set(
                ((event.clientX - rect.left) / rect.width) * 2 - 1,
                -(((event.clientY - rect.top) / rect.height) * 2 - 1)
            );
        };
        currentMount.addEventListener('mousemove', handleMouseMove);

        const handleResize = () => {
            renderer.setSize(currentMount.clientWidth, currentMount.clientHeight);
            camera.aspect = currentMount.clientWidth / currentMount.clientHeight;
            camera.updateProjectionMatrix();
        };
        window.addEventListener('resize', handleResize);

        const animate = () => {
            requestAnimationFrame(animate);
            const elapsedTime = clockRef.current.getElapsedTime();
            cardMaterial.uniforms.uTime.value = elapsedTime;
            cardMaterial.uniforms.uMouse.value.copy(mousePos);

            let easedProgress = 0; // <<< VARIÁVEL PARA CONTROLAR A INTENSIDADE DO EFEITO

            if (isHoveringRef.current) {
                finalTargetRotation.set(
                    -mousePos.y * ANIMATION_CONFIG.MOUSE_ROTATION_SENSITIVITY,
                    mousePos.x * ANIMATION_CONFIG.MOUSE_ROTATION_SENSITIVITY
                );
                easedProgress = 1.0; // Efeito holo no máximo quando o mouse está sobre
            } else {
                const { IDLE_TURN_DURATION, IDLE_PAUSE_DURATION, IDLE_MAX_ROTATION_ANGLE } = ANIMATION_CONFIG;
                const phaseTurnReturn = IDLE_TURN_DURATION;
                const phasePause = IDLE_PAUSE_DURATION;
                
                const timeTurnLeft = phaseTurnReturn;
                const timeReturnFromLeft = timeTurnLeft + phaseTurnReturn;
                const timePauseCenter = timeReturnFromLeft + phasePause;
                const timeTurnRight = timePauseCenter + phaseTurnReturn;
                const timeReturnFromRight = timeTurnRight + phaseTurnReturn;
                const idleLoopDuration = timeReturnFromRight + phasePause;

                const loopTime = elapsedTime % idleLoopDuration;
                let progress = 0;
                let direction = 0;

                if (loopTime < timeTurnLeft) {
                    progress = loopTime / phaseTurnReturn; direction = 1;
                } else if (loopTime < timeReturnFromLeft) {
                    progress = 1.0 - ((loopTime - timeTurnLeft) / phaseTurnReturn); direction = 1;
                } else if (loopTime < timePauseCenter) {
                    progress = 0; direction = 0;
                } else if (loopTime < timeTurnRight) {
                    progress = (loopTime - timePauseCenter) / phaseTurnReturn; direction = -1;
                } else if (loopTime < timeReturnFromRight) {
                    progress = 1.0 - ((loopTime - timeTurnRight) / phaseTurnReturn); direction = -1;
                } else {
                    progress = 0; direction = 0;
                }
                
                easedProgress = easeInOutSine(progress);
                finalTargetRotation.set(0, easedProgress * IDLE_MAX_ROTATION_ANGLE * direction);
            }

            smoothTargetRotation.lerp(finalTargetRotation, ANIMATION_CONFIG.TARGET_DAMPING_FACTOR);

            cardMesh.rotation.x += (smoothTargetRotation.x - cardMesh.rotation.x) * ANIMATION_CONFIG.ROTATION_DAMPING_FACTOR;
            cardMesh.rotation.y += (smoothTargetRotation.y - cardMesh.rotation.y) * ANIMATION_CONFIG.ROTATION_DAMPING_FACTOR;
            
            // <<< A MÁGICA FINAL >>>
            // A intensidade da luz do cursor é controlada pelo hover
            const targetCursorIntensity = isHoveringRef.current ? effectParams.cursorIntensity : 0;
            cardMaterial.uniforms.uParam3.value += (targetCursorIntensity - cardMaterial.uniforms.uParam3.value) * ANIMATION_CONFIG.CURSOR_LIGHT_FADE_SPEED;
            
            // A refletividade geral do holo é controlada pelo progresso do movimento
            const targetReflectivity = effectParams.reflectivity * easedProgress;
            cardMaterial.uniforms.uParam2.value += (targetReflectivity - cardMaterial.uniforms.uParam2.value) * 0.1; // Suaviza a refletividade
            
            renderer.render(scene, camera);
        };
        animate();

        // Lógica de desenho do canvas (sem alterações)
        const ctx = canvas.getContext('2d');
        const drawCard = (bgImage) => {
            ctx.fillStyle = '#111827'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            if (bgImage) {
                const canvasAspect = canvas.width / canvas.height; const imageAspect = bgImage.width / bgImage.height;
                let dw, dh, dx, dy;
                if (imageAspect > canvasAspect) {
                    dh = canvas.height; dw = dh * imageAspect; dx = (canvas.width - dw) / 2; dy = 0;
                } else {
                    dw = canvas.width; dh = dw / imageAspect; dx = 0; dy = (canvas.height - dh) / 2;
                }
                ctx.drawImage(bgImage, dx, dy, dw, dh);
            }
            ctx.fillStyle = 'rgba(0, 0, 0, 0.3)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 3;
            ctx.strokeRect(50, 80, canvas.width - 100, canvas.height - 160);
            ctx.lineWidth = 1;
            ctx.strokeRect(65, 65, canvas.width - 130, canvas.height - 130);
            ctx.shadowColor = 'rgba(0,0,0,0.7)'; ctx.shadowBlur = 10;
            ctx.fillStyle = '#FFFFFF'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.font = 'bold 80px sans-serif'; ctx.fillText(cardContent.leagueName.toUpperCase(), canvas.width / 2, 230);
            ctx.font = '60px sans-serif'; ctx.fillText(cardContent.placement.toUpperCase(), canvas.width / 2, canvas.height - 280);
            ctx.font = 'bold 70px sans-serif'; ctx.fillText(cardContent.playerName.toUpperCase(), canvas.width / 2, canvas.height - 170);
            ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0;
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.fillRect(400, canvas.height - 230, canvas.width - 800, 2);
            canvasTexture.needsUpdate = true;
        };
        const image = new Image();
        image.crossOrigin = 'Anonymous';
        image.onload = () => drawCard(image);
        image.onerror = () => drawCard(null);
        image.src = imageUrl;

        return () => {
            // Limpeza
            currentMount.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('resize', handleResize);
            if (currentMount && renderer.domElement) {
                currentMount.removeChild(renderer.domElement);
            }
            renderer.dispose();
            cardGeometry.dispose();
            cardMaterial.dispose();
            canvasTexture.dispose();
            loadedFoilTexture.dispose();
        };
    }, [imageUrl, title]);

    return (
        <div
            ref={mountRef}
            className="w-full h-full"
            onMouseEnter={() => { isHoveringRef.current = true; }}
            onMouseLeave={() => { isHoveringRef.current = false; }}
        />
    );
};

export default HoloCard;