---
layout: default
title: "Astro 5.10 تحديثات قوية للصور والمحتوى وأمن المواقع
"
image: "https://d4.alternativeto.net/UoGcjQIhZ1KdF-XRqzrTTRm-APvEf6h15xzQFOsJsAY/rs:fill:1520:760:0/g:ce:0:0/YWJzOi8vZGlzdC9jb250ZW50LzE3NTA0NTE4NjU5NTMucG5n.png"
category: أنظمة
date: 2025-06-20T20:27:15
---

أطلق Astro 5.10 تحديثًا هامًا يركز على تحسين تجربة المستخدم وتسريع الأداء، حيث يقدم ميزة "مجموعات المحتوى الحي" التجريبية التي تمكن المطورين من جلب البيانات في وقت التشغيل بدلاً من وقت الإنشاء، مما يتيح عرض محتوى مُحدَّث باستمرار أو مُخصَّص دون الحاجة لإعادة بناء الموقع بالكامل. تعتمد هذه الميزة على مُحمّلات حية جديدة تجلب البيانات مع كل طلب، ويمكن تفعيلها عبر علامة `liveContentCollections` وتحديد مصادر البيانات في ملف تهيئة مخصص.

بالإضافة إلى ذلك، أصبح دعم الصور المتجاوبة ميزة مستقرة في هذا الإصدار، حيث يقوم Astro الآن بإنشاء `srcset` و `sizes` وتصميمات مُحسّنة تلقائيًا، مما يضمن أداءً ممتازًا للصور على جميع أحجام الشاشات. يمكن للمطورين تحديد سلوكيات الاستجابة بشكل عام أو لكل مكون على حدة، كما تتيح خاصية `priority` الجديدة تحميل الصور الهامة بشكل فوري، مما يساعد على تحسين مقياس Largest Contentful Paint.

كما وسع Astro 5.10 دعمه التجريبي لسياسة أمان المحتوى (CSP)، مما يجعل من الممكن إنشاء رؤوس CSP لكل من الصفحات الديناميكية والثابتة. تقدم الصفحات حسب الطلب الآن رؤوس CSP بدلاً من علامات التعريف الوصفية، مما يتيح استخدام توجيهات إضافية مثل `report-uri` و `frame-ancestors`. بالنسبة لعمليات النشر المتقدمة، يقدم الإصدار دعمًا لنقاط دخول مخصصة في Cloudflare Workers، مما يسمح بحالات استخدام مثل Durable Objects و Queues و Cron Triggers.

<div style="margin-top:2px; margin-bottom:2px;"><a href="https://bidjadraft.github.io/?query=Astro" style="background:#e3f2fd; color:#1565c0; font-size:80%; border-radius:12px; padding:3px 10px; margin:2px 4px 2px 0; display:inline-block; border:1px solid #bbdefb; text-decoration:none;">Astro</a> <a href="https://bidjadraft.github.io/?query=Cloudflare" style="background:#e3f2fd; color:#1565c0; font-size:80%; border-radius:12px; padding:3px 10px; margin:2px 4px 2px 0; display:inline-block; border:1px solid #bbdefb; text-decoration:none;">Cloudflare</a> <a href="https://bidjadraft.github.io/?query=Workers" style="background:#e3f2fd; color:#1565c0; font-size:80%; border-radius:12px; padding:3px 10px; margin:2px 4px 2px 0; display:inline-block; border:1px solid #bbdefb; text-decoration:none;">Workers</a></div><br><br>
