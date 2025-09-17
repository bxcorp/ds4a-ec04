package com.tuempresa.http.compat

import java.net.{URI, URLEncoder}
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration
import java.nio.charset.StandardCharsets
import scala.collection.mutable

// ===== Tipos "compatibles" mínimos para no usar Spring =====

final class MediaType private (val value: String)
object MediaType {
  val APPLICATION_JSON: MediaType             = new MediaType("application/json")
  val APPLICATION_FORM_URLENCODED: MediaType = new MediaType("application/x-www-form-urlencoded")
}

final class HttpHeaders {
  private val map = new mutable.LinkedHashMap[String, String]()
  private var _contentType: MediaType = null
  private var _contentLength: Long = -1L

  def setContentType(mt: MediaType): Unit = { _contentType = mt; set("Content-Type", mt.value) }
  def setContentLength(n: Long): Unit = { _contentLength = n; set("Content-Length", n.toString) }
  def add(name: String, value: String): Unit = set(name, value)
  def set(name: String, value: String): Unit = map.update(name, value)
  def get(name: String): Option[String] = map.get(name)
  def asMap: Map[String, String] = map.toMap

  // atajos comunes
  def setPragma(v: String): Unit = set("Pragma", v)
  def setExpires(v: Long): Unit = set("Expires", v.toString)
  def setCacheControl(v: String): Unit = set("Cache-Control", v)
}

sealed trait HttpMethod
object HttpMethod {
  case object GET  extends HttpMethod
  case object POST extends HttpMethod
}

final case class HttpStatus(code: Int) {
  def is4xxClientError: Boolean = code >= 400 && code < 500
  def is5xxServerError: Boolean = code >= 500 && code < 600
  override def toString: String = s"$code"
}

final class HttpEntity[T](val body: T, val headers: HttpHeaders) {
  def this(headers: HttpHeaders) = this(null.asInstanceOf[T], headers)
}

final class ResponseEntity[T](private val status: Int, private val _body: T) {
  def getStatusCode: HttpStatus = HttpStatus(status)
  def getBody: T = _body
}

// MultiValueMap muy simple (para form-urlencoded)
trait MultiValueMap[K, V] {
  def add(key: K, value: V): Unit
  def toScala: Map[K, List[V]]
}
final class LinkedMultiValueMap[K, V] extends MultiValueMap[K, V] {
  private val inner = new mutable.LinkedHashMap[K, mutable.ListBuffer[V]]()
  def add(key: K, value: V): Unit =
    inner.getOrElseUpdate(key, mutable.ListBuffer[V]()) += value
  def toScala: Map[K, List[V]] = inner.view.mapValues(_.toList).toMap
}

// ===== RestTemplate "compatible" usando Java 11 HttpClient =====

class RestTemplate(connectTimeoutSeconds: Int = 5, readTimeoutSeconds: Int = 30) {

  private val http: HttpClient = HttpClient.newBuilder()
    .connectTimeout(Duration.ofSeconds(connectTimeoutSeconds.toLong))
    .build()

  // mimetiza: restTemplate.exchange(url, HttpMethod.GET, new HttpEntity[AnyRef](headers), classOf[String])
  def exchange(url: String,
               method: HttpMethod,
               entity: HttpEntity[_],
               responseType: Class[String]): ResponseEntity[String] = {

    val timeout = Duration.ofSeconds(readTimeoutSeconds.toLong)
    val builder = HttpRequest.newBuilder(URI.create(url))
      .timeout(timeout)

    // headers
    entity.headers.asMap.foreach { case (k, v) => builder.header(k, v) }

    val req = method match {
      case HttpMethod.GET =>
        builder.GET().build()

      case HttpMethod.POST =>
        val (publisher, maybeCT) = bodyPublisherFor(entity)
        // si no habían puesto content-type y nosotros sabemos uno, agréguelo
        if (maybeCT.nonEmpty && entity.headers.get("Content-Type").isEmpty)
          builder.header("Content-Type", maybeCT.get)
        builder.POST(publisher).build()
    }

    val resp = http.send(req, HttpResponse.BodyHandlers.ofString())
    new ResponseEntity[String](resp.statusCode(), resp.body())
  }

  // mimetiza: restTemplate.postForEntity(url, new HttpEntity[String](json, headers), classOf[String])
  def postForEntity(url: String,
                    entity: HttpEntity[_],
                    responseType: Class[String]): ResponseEntity[String] =
    exchange(url, HttpMethod.POST, entity, responseType)

  // ===== Helpers =====

  private def bodyPublisherFor(entity: HttpEntity[_]): (HttpRequest.BodyPublisher, Option[String]) = {
    val ct = entity.headers.get("Content-Type")
    entity.body match {
      case null =>
        (HttpRequest.BodyPublishers.noBody(), None)

      case s: String =>
        val bytes = s.getBytes(StandardCharsets.UTF_8)
        (HttpRequest.BodyPublishers.ofByteArray(bytes), ct.orElse(Some("text/plain; charset=UTF-8")))

      case mvm: MultiValueMap[String, String] =>
        val encoded = toFormUrlEncoded(mvm)
        val bytes = encoded.getBytes(StandardCharsets.UTF_8)
        (HttpRequest.BodyPublishers.ofByteArray(bytes), Some(MediaType.APPLICATION_FORM_URLENCODED.value))

      case other =>
        val s = other.toString
        val bytes = s.getBytes(StandardCharsets.UTF_8)
        (HttpRequest.BodyPublishers.ofByteArray(bytes), ct.orElse(Some("text/plain; charset=UTF-8")))
    }
  }

  private def toFormUrlEncoded(mvm: MultiValueMap[String, String]): String = {
    def enc(s: String) = URLEncoder.encode(s, StandardCharsets.UTF_8.name())
    mvm.toScala
      .toSeq
      .flatMap { case (k, vs) => vs.map(v => s"${enc(k)}=${enc(v)}") }
      .mkString("&")
  }
}